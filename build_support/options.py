"""handles command-line options to build.py, and makes them available to build routines"""
import argparse, os, sys

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

class Options(object):
    def __init__(self, args=None):
        self.prog = None
        self.component_dir = None
        self._parser = argparse.ArgumentParser(description="argument parser for mesa jenkins build wrapper")
        self._parser.add_argument('--action', type=str, default=["build"],
                                  choices=CsvChoice('build', 'clean', 'test', 'jenkins'),
                                  action=CsvAction,
                                  help="Action to recurse with. 'build', 'clean' or 'test'. (default: %(default)s)")
        self._parser.add_argument('--config', type=str, default="release", choices=['release', 'debug'],
                                  help="Release or Debug build. (default: %(default)s)")
        self._parser.add_argument('--type', type=str, default="developer",
                                  choices=['developer', 'percheckin', 'daily', 'release'],
                                  help="The source of the build trigger. (default: %(default)s)")
        self._parser.add_argument('--arch', type=str, 
                                  default='m64', choices=['m64', 'm32'],
                                  help="The architecture for the target build. (default: %(default)s)")
        self._parser.add_argument('--hardware', type=str, default='builder',
                                  help="The hardware to be targeted for test ('builder', 'snb', 'ivb', 'hsw', 'bdw'). "
                                  "(default: %(default)s)")
        self._parser.add_argument('--prerequisites', type=str, default='recurse',
                                  choices=['recurse', 'collect', 'ignore'],
                                  help="Specify how to handle prerequisites. \n"
                                  "\tIgnore: do nothing with the prerequisites. \n" 
                                  "\tCollect: take built prerequisites.\n"
                                  "\tRecurse: build prerequisites. (default: %(default)s)")
        self._parser.add_argument('--result_path', type=str, default='',
                                  help="The location on the build master for placing and fetching built binaries.")
        
        self.update_arg0(sys.argv[0])
        if args is not None:
            self.update_arg0(args[0])
            args = args[1:]

        # list out the members, so pylint doesn't get confused
        self.action = []
        self.arch = ""
        self.hardware = ""
        self.config = ""
        self.type = ""
        self.result_path = ""
        self.prerequisites = ""
        # Parse the args and explode it into the Options class
        self.__dict__.update(vars(self._parser.parse_args(args)))

    def to_string(self):
        arglist = []
        arglist += ["--action", ','.join(self.action)]
        arglist += ["--arch", self.arch]
        arglist += ["--hardware", self.hardware]
        arglist += ["--config", self.config]
        arglist += ["--type", self.type]
        if self.result_path != "":
            arglist += ["--result_path", self.result_path]
        arglist += ["--prerequisites", self.prerequisites]

        return " ".join(arglist)

    def update_arg0(self, arg0=None):
        # We should really do better for this:
        self.prog = arg0
        self.component_dir = os.path.dirname(os.path.abspath(arg0))

