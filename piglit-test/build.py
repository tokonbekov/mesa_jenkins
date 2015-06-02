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
        

bs.build(bs.PiglitTester(_suite="gpu"), time_limit=SlowTimeout())
