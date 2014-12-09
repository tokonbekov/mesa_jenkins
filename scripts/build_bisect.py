import os, sys, signal, argparse, re
import time
import xml.etree.ElementTree as ET
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs


def bisect(project, args, commits):
    if not commits:
        return
    current_build = len(commits) / 2
    rev = project + "=" + commits[current_build].hexsha
    print "Range: " + commits[0].hexsha + " - " + commits[-1].hexsha
    print "Building revision: " + rev

    # remove inadvertent whitespace, which is easy to add when
    # triggering builds on jenkins
    test_name = args.test_name.strip()

    hw_arch = test_name.split(".")[-1]
    o = bs.Options(args=["ignore"])
    o.type = "developer"
    o.config = "debug"
    o.arch = hw_arch[-3:]
    o.hardware = hw_arch[:-3]
    o.action = ["build", "test"]

    revspec = bs.RevisionSpecification(from_cmd_line=[rev])
    revspec.checkout()
    revspec = bs.RevisionSpecification()
    hashstr = revspec.to_cmd_line_param().replace(" ", "_")
    spec_xml = bs.ProjectMap().build_spec()
    results_dir = spec_xml.find("build_master").attrib["results_dir"]
    result_path = "/".join([results_dir, "mesa_master", hashstr, "bisect"])
    o.result_path = result_path
    bs.rmtree(result_path + "/test")

    global jen
    jen = bs.Jenkins(result_path=result_path,
                     revspec=revspec)
    
    depGraph = bs.DependencyGraph("piglit-test", o)
    # remove test build from graph, because we always want to build
    # it.
    bi = bs.ProjectInvoke(project="piglit-test", 
                          options=o)
    bi.set_info("status", "bisect-rebuild")

    depGraph.build_complete(bi)
    try:
        jen.build_all(depGraph, "bisect")
        print "Starting: " + bi.to_short_string()
        test_name_good_chars = re.sub('[_ !:]', ".", test_name)
        jen.build(bi, branch="mesa_master", extra_arg="--piglit_test=" + test_name_good_chars)
        jen.wait_for_build()
    except bs.BuildFailure:
        print "BUILD FAILED - exception: " + rev
        if current_build + 1 == len(commits):
            print "FIRST DETECTED FAILURE: " + rev
            return
        return bisect(project, args, commits[current_build+1:])

    test_result = "/".join([result_path, "test", "piglit-test_" + 
                            o.hardware + "_" + o.arch + ".xml"])
    iteration = 0
    while not os.path.exists(test_result):
        if iteration < 40:
            time.sleep(1)
            iteration = iteration + 1
            continue
        print "BUILD FAILED - no test results: " + rev + " : " + test_result
        if current_build + 1 == len(commits):
            print "FIRST DETECTED FAILURE: " + rev
            return
        return bisect(project, args, commits[current_build + 1:])

    result = ET.parse(test_result)
    for testcase in result.findall("./testsuite/testcase"):
        testname = testcase.attrib["classname"] + "." + testcase.attrib["name"]
        if testname != test_name:
            continue
        if testcase.findall("skipped"):
            print "ERROR: the target test was skipped"
        if testcase.findall("failure") or testcase.findall("error"):
            print "TEST FAILED: " + rev
            if current_build + 1 == len(commits):
                print "FIRST DETECTED FAILURE: " + rev
                return
            return bisect(project, args, commits[current_build + 1:])

        print "TEST PASSED: " + rev
        if current_build == 0:
            print "LAST DETECTED SUCCESS: " + rev
            return
        return bisect(project, args, commits[:current_build])

    print "ERROR -- TEST NOT FOUND: " + test_name
    if current_build == 0:
        print "LAST DETECTED SUCCESS: " + rev
        return
    return bisect(project, args, commits[:current_build])

def main():
    description="searches for revision triggering a specific piglit test failure"
    parser= argparse.ArgumentParser(description=description, 
                                    conflict_handler="resolve")

    parser.add_argument('--good_revision', type=str, required=True,
                        help="revision where test passes")

    parser.add_argument('--bad_revision', type=str, required=True,
                        help="revision where test fails")

    parser.add_argument('--test_name', type=str, required=True,
                        help="test to search for")

    parser.add_argument('--base_revision', type=str, default="",
                        help="revisions for projects other than mesa, defaults to master")
    
    args = parser.parse_args()

    repos = bs.RepoSet()
    repos.fetch()

    # get tip, which will be the base_revision unless the user has
    # specified something
    bspec = bs.BuildSpecification()
    bspec.checkout("mesa_master")
    
    base_revision = args.base_revision
    if base_revision:
        cmd_line = base_revision.split(" ")
        revspec = bs.RevisionSpecification(from_cmd_line=cmd_line)
        revspec.checkout()
        
    project = "mesa"
    for project in ["mesa", "piglit-build", "waffle", "drm"]:
        try:
            revspec = bs.RevisionSpecification(from_cmd_line=[project + "=" + args.bad_revision])
            revspec.checkout()
        except:
            print args.bad_revision + " not found in " + project
            continue

        print args.bad_revision + " found in " + project
        break

    target_repo = repos.repo(project)
    commits = []
    good_revision = args.good_revision
    print "Revision History:"
    for commit in target_repo.iter_commits(max_count=1000):
        commits.append(commit)
        if good_revision in commit.hexsha:
            break
        print "    " + commit.hexsha

    if good_revision not in commits[-1].hexsha:
        print "ERROR: could not find " + good_revision + \
            " in history of " + args.bad_revision
        sys.exit(-1)

    bisect(project, args, commits)

if __name__=="__main__":
    main()
