#!/usr/bin/python

import argparse, sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

class CsvChoice(object):
    def __init__(self, *args):
        self.values = args
    def __len__(self):
        return self.values.__len__()
    def __iter__(self):
        return self.values.__iter__()

    def __contains__(self, choice):
        # If we were not passed a string, it isn't contained here
        if type(choice) != str:
            return False
        result = True
        for i in choice.split(','):
            result &= i in self.values
        return result

class CsvAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values.split(','))

def main():
    parser = argparse.ArgumentParser(description='Build projects locally.')

    parser.add_argument('--action', type=str, default=["build"],
                        choices=CsvChoice('build', 'clean', 'test'),
                        action=CsvAction,
                        help="Action to recurse with. 'build', 'clean' or 'test'. (default: %(default)s)")
    parser.add_argument('--project', dest='project', type=str, default="all-test",
                        help='project to build. (default: %(default)s)')
    parser.add_argument('--arch', dest='arch', type=str, 
                        default='m64', choices=['m64', 'm32'],
                        help='arch to build. (default: %(default)s)')
    parser.add_argument('--config', type=str, default="release", choices=['release', 'debug'],
                        help="Release or Debug build. (default: %(default)s)")
    parser.add_argument('--type', type=str, default="developer",
                        choices=['developer', 'percheckin', 'daily', 'release'],
                        help="category of tests to run. (default: %(default)s)")
    parser.add_argument('--branch', type=str, default="mesa_master",
                        help="Branch specification to build.  See build_specification.xml/branches")

    args = parser.parse_args()
    project = args.project
    o = bs.Options(["bogus"])
    vdict = vars(args)
    del vdict["project"]
    o.__dict__.update(vdict)

    bs.rmtree(bs.ProjectMap().build_root())

    graph = bs.DependencyGraph(project, o)
    ready = graph.ready_builds()
    pm = bs.ProjectMap()
    while ready:
        for bi in ready:
            graph.build_complete(bi)
            os.chdir(pm.project_build_dir(bi.project))
            if os.path.exists("build.py"):
                bs.run_batch_command([sys.executable, "build.py"] +  o.to_string().split(" "))
        ready = graph.ready_builds()

main()
