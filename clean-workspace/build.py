#!/usr/bin/python

import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

class Cleaner(object):
    def __init__(self):
        pass

    def clean(self):
        bs.run_batch_command(["git", "clean", "-xfd"])
        bs.run_batch_command(["git", "reset", "--hard", "HEAD"])
        bs.rmtree("repos")

    def build(self):
        pass

    def test(self):
        pass

bs.build(Cleaner())

        
