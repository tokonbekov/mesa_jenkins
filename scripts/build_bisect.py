import os, sys, signal, argparse
import time
import xml.etree.ElementTree as ET
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

triggered_builds_str = []
jen = None

def abort_builds(ignore, _):
    for an_invoke_str in triggered_builds_str:
        jen.abort(bs.ProjectInvoke(from_string=an_invoke_str))
    raise bs.BuildAborted()

def bisect(args, commits):
    if not commits:
        return
    current_build = len(commits) / 2
    rev = "mesa=" + commits[current_build].hexsha
    print "Range: " + commits[0].hexsha + " - " + commits[-1].hexsha
    print "Building revision: " + rev

    hw_arch = args.test_name.split(".")[-1]
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
        jen.build_all(depGraph, triggered_builds_str, "bisect")
        print "Starting: " + bi.to_short_string()
        jen.build(bi, branch="mesa_master", extra_arg="--piglit_test=" + args.test_name)
        jen.wait_for_build()
    except bs.BuildFailure:
        print "BUILD FAILED - exception: " + rev
        if current_build + 1 == len(commits):
            print "FIRST DETECTED FAILURE: " + rev
            return
        return bisect(args, commits[current_build+1:])

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
        return bisect(args, commits[current_build + 1:])

    result = ET.parse(test_result)
    for testcase in result.findall("./testsuite/testcase"):
        testname = testcase.attrib["classname"] + "." + testcase.attrib["name"]
        if testname != args.test_name:
            continue
        if testcase.findall("skipped"):
            print "ERROR: the target test was skipped"
        if testcase.findall("failure") or testcase.findall("error"):
            print "TEST FAILED: " + rev
            if current_build + 1 == len(commits):
                print "FIRST DETECTED FAILURE: " + rev
                return
            return bisect(args, commits[current_build + 1:])

        print "TEST PASSED: " + rev
        if current_build == 0:
            print "LAST DETECTED SUCCESS: " + rev
            return
        return bisect(args, commits[:current_build])
    print "ERROR -- TEST NOT FOUND: " + args.test_name

def main():
    signal.signal(signal.SIGINT, abort_builds)
    signal.signal(signal.SIGABRT, abort_builds)
    signal.signal(signal.SIGTERM, abort_builds)

    description="searches for revision triggering a specific piglit test failure"
    parser= argparse.ArgumentParser(description=description, 
                                    conflict_handler="resolve")

    parser.add_argument('--good_revision', type=str, required=True,
                        help="revision where test passes")

    parser.add_argument('--bad_revision', type=str, required=True,
                        help="revision where test fails")

    parser.add_argument('--test_name', type=str, required=True,
                        help="test to search for")
    
    args = parser.parse_args()

    repos = bs.RepoSet()
    repos.fetch()

    revspec = bs.RevisionSpecification(from_cmd_line=["mesa=" + args.bad_revision])
    revspec.checkout()

    mesa_repo = repos.repo("mesa")
    commits = []
    good_revision = args.good_revision
    print "Revision History:"
    for commit in mesa_repo.iter_commits(max_count=1000):
        commits.append(commit)
        if good_revision in commit.hexsha:
            break
        print "    " + commit.hexsha

    if good_revision not in commits[-1].hexsha:
        print "ERROR: could not find " + good_revision + \
            " in history of " + args.bad_revision
        sys.exit(-1)

    bisect(args, commits)

if __name__=="__main__":
    main()
