import argparse
import datetime
import os
import sys
import time
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

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

    parser.add_argument('--revision', type=str, default="",
                        help="mesa revision to test.")

    args = parser.parse_args()
    projects = []
    if args.project:
        projects = args.project.split(",")
    revision = args.revision

    # some build_local params are not handled by the Options, which is
    # used by other modules.  This code strips out incompatible args
    o = bs.Options(["bogus"])
    vdict = vars(args)
    del vdict["project"]
    del vdict["revision"]
    o.__dict__.update(vdict)
    sys.argv = ["bogus"] + o.to_list()

    bspec = bs.BuildSpecification()

    pm = bs.ProjectMap()
    bs.rmtree(pm.source_root() + "/test_summary.txt")

    # checkout the desired revision on top of recent revisions
    bspec.checkout("mesa_master")
    revspec = None
    if (revision):
        revspec = bs.RevisionSpecification(from_cmd_line=revision.split())
        revspec.checkout()

    revspec = bs.RevisionSpecification()
    hashstr = "mesa=" + revspec.revision("mesa")
    print "Building revision: " + hashstr

    # create a result_path that is unique for this set of builds
    spec_xml = pm.build_spec()
    results_dir = spec_xml.find("build_master").attrib["results_dir"]
    result_path = "/".join([results_dir, "perf", hashstr])
    o.result_path = result_path

    for a_perf_dir in ["egypt", "xonotic"]:
        # remove prior build status files.  We want to rebuild perf
        # results by default
        status_dir = result_path + "/" + a_perf_dir
        if (os.path.exists(status_dir)):
            bs.rmtree(status_dir)

    if not projects:
        projects = ["perf-all"]

    # use a global, so signal handler can abort builds when scheduler
    # is interrupted
    global jen

    jen = bs.Jenkins(result_path=result_path,
                     revspec=revspec)

    depGraph = bs.DependencyGraph(projects, o)

    # use a global, so signal handler can abort builds when scheduler
    # is interrupted
    try:
        jen.build_all(depGraph, branch="mesa_master")
    except Exception as e:
        print "ERROR: encountered failure: " + str(e)
        raise

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
