import os, sys, signal, argparse, re
import time
import xml.etree.ElementTree as ET
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs



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

    hw_arch = args.test_name.split(".")[-1]
    arch = hw_arch[-3:]
    hardware = hw_arch[:-3]

    test_name = args.test_name.split(".")[:-1]

    b = bs.Bisector(project, test_name, arch, hardware, commits)
    print "FIRST FAILURE: " + b.Bisect()

if __name__=="__main__":
    main()
