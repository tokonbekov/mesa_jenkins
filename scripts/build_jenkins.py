import os, time, sys, shutil, hashlib, argparse, shutil
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs


def collate_tests(result_path, out_test_dir):
    src_test_dir = result_path + "/test"
    print "collecting tests from " + src_test_dir
    i = 0
    while i < 10 and not os.path.exists(src_test_dir):
        i += 1
        print "sleeping, waiting fort test directory: " + src_test_dir
        time.sleep(10)
    if not os.path.exists(src_test_dir):
        print "no test directory found: " + src_test_dir
        return
        
    cmd = ["cp", "-a", "-n",
           src_test_dir,
           out_test_dir]
    bs.run_batch_command(cmd)

def main():

    # reuse the options from the gasket
    o = bs.Options([sys.argv[0]])
    description="builds a component on jenkins"
    parser= argparse.ArgumentParser(description=description, 
                                    parents=[o._parser], 
                                    conflict_handler="resolve")
    parser.add_argument('--project', dest='project', type=str, default="",
                        help='Project to build. Default project is specified '\
                        'for the branch in build_specification.xml')

    parser.add_argument('--branch', type=str, default="mesa_master",
                        help="Branch specification to build.  "\
                        "See build_specification.xml/branches")

    parser.add_argument('--revision', type=str, default="",
                        help="specific set of revisions to build.")

    parser.add_argument('--rebuild', type=str, default="false",
                        choices=['true', 'false'], 
                        help="specific set of revisions to build."
                        "(default: %(default)s)")


    args = parser.parse_args()
    projects = []
    if args.project:
        projects = args.project.split(",")
    branch = args.branch
    revision = args.revision
    rebuild = args.rebuild

    # some build_local params are not handled by the Options, which is
    # used by other modules.  This code strips out incompatible args
    o = bs.Options(["bogus"])
    vdict = vars(args)
    del vdict["project"]
    del vdict["branch"]
    del vdict["revision"]
    del vdict["rebuild"]
    o.__dict__.update(vdict)
    sys.argv = ["bogus"] + o.to_string().split()

    bspec = bs.BuildSpecification()

    pm = bs.ProjectMap()
    bs.rmtree(pm.source_root() + "/test_summary.txt")

    # start with the specified branch, then layer any revision spec on
    # top of it
    bspec.checkout(branch)
    revspec = None
    if (revision):
        revspec = bs.RevisionSpecification(from_cmd_line=revision.split())
        revspec.checkout()

    revspec = bs.RevisionSpecification()
    print "Building revision: " + revspec.to_cmd_line_param()

    hashstr = revspec.to_cmd_line_param().replace(" ", "_")

    # create a result_path that is unique for this set of builds
    spec_xml = pm.build_spec()
    results_dir = spec_xml.find("build_master").attrib["results_dir"]
    result_path = "/".join([results_dir, branch, hashstr, o.type])
    o.result_path = result_path

    if rebuild == "true" and os.path.exists(result_path):
        print "Removing existing results."
        bs.rmtree(result_path)

    if not projects:
        branchspec = bspec.branch_specification(branch)
        projects = [branchspec.project]

    # use a global, so signal handler can abort builds when scheduler
    # is interrupted
    global jen

    jen = bs.Jenkins(result_path=result_path,
                     revspec=revspec)


    depGraph = bs.DependencyGraph(projects, o)

    out_test_dir = pm.output_dir()
    if os.path.exists(out_test_dir):
        bs.rmtree(out_test_dir)
    os.makedirs(out_test_dir)

    # to collate all logs in the scheduler
    out_log_dir = pm.output_dir()
    if os.path.exists(out_log_dir):
        bs.rmtree(out_log_dir)
    os.makedirs(out_log_dir)

    # use a global, so signal handler can abort builds when scheduler
    # is interrupted
    try:
        jen.build_all(depGraph, branch=branch)
    finally:
        collate_tests(result_path, out_test_dir)
        bs.rmtree("test_summary.txt")
        fh = open("test_summary.txt", "w")
        tl = bs.TestLister(out_test_dir + "/test")
        for atest in tl.Tests():
            atest.PrettyPrint(fh)
        fh.close()

if __name__=="__main__":
    try:
        main()
    except SystemExit:
        # Uncomment to determine which version of argparse is throwing
        # us under the bus.

        #  Word of Wisdom: Don't call sys.exit
        #import traceback
        #for x in traceback.format_exception(*sys.exc_info()):
        #    print x
        raise
