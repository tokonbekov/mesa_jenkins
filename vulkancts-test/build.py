#!/usr/bin/python

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

class SlowTimeout:
    def __init__(self):
        pass

    def GetDuration(self):
        return 500

bs.build(bs.DeqpBuilder(["vk"]), time_limit=SlowTimeout())

