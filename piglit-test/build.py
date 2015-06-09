#!/usr/bin/python

import sys, os, argparse
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

class SlowTimeout:
    def __init__(self):
        self.hardware = bs.Options().hardware

    def GetDuration(self):
        if self.hardware == "bsw":
            return 120
        if self.hardware == "byt":
            return 120
        if self.hardware == "g33":
            return 120
        if self.hardware == "g965":
            return 50
        # all other test suites finish in 10 minutes or less.
        # TODO: put back to 25 when curro's regression is fixed
        return 40
        
# add the --piglit_test option to the standard options.  Parse the
# options, and strip the piglit_test so the options will work as usual
# for subsequent objects.
o = bs.Options([sys.argv[0]])
parser= argparse.ArgumentParser(description="piglit args allow a specific test", 
                                parents=[o._parser], 
                                conflict_handler="resolve")
parser.add_argument('--piglit_test', type=str, default="",
                    help="single piglit test to run.")

args = parser.parse_args()
piglit_test = ""
if args.piglit_test:
    piglit_test = args.piglit_test

vdict = vars(args)
del vdict["piglit_test"]
o.__dict__.update(vdict)
sys.argv = [sys.argv[0]] + o.to_string().split()


bs.build(bs.PiglitTester(_suite="gpu",
                         piglit_test=piglit_test),
         time_limit=SlowTimeout())
