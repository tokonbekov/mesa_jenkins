#!/usr/bin/python

import sys, os, argparse
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

class SlowTimeout:
    def __init__(self, options):
        self.hardware = options.hardware

    def GetDuration(self):
        if self.hardware == "byt":
            return 120
        if self.hardware == "g965":
            return 50
        # all other test suites finish in 10 minutes or less.
        return 25
        

_o = bs.Options([sys.argv[0]])
parser= argparse.ArgumentParser(description="Allows additional parameters for "\
                                "specifying test", 
                                parents=[_o._parser], 
                                conflict_handler="resolve")
parser.add_argument('--piglit_test', dest='piglit_test', type=str, default="",
                    help="specify test to run, passed to piglit --include-tests "\
                    "param.  Name should be the full test as it appears in "\
                    "jenkins, including the hw/arch suffix")

args = parser.parse_args()
piglit_test = None
if args.piglit_test:
    piglit_test = args.piglit_test

# strip out --piglit_test from arguments, because it will not be
# handled by any other arg parser.
vdict = vars(args)
del vdict["piglit_test"]
_o = bs.Options(["bogus"])
_o.__dict__.update(vdict)
sys.argv = [sys.argv[0]] + _o.to_string().split()

# if we are running a bisect, then the target may be in either the cpu
# or the gpu suite.  Use the quick suite, which is more comprehensive
suite = "gpu"
if piglit_test:
    suite = "quick"

bs.build(bs.PiglitTester(piglit_test, _suite=suite), time_limit=SlowTimeout(_o))
