#!/usr/bin/python

import os
import sys
import subprocess

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs


class SlowTimeout:
    def __init__(self):
        self.hardware = bs.Options().hardware

    def GetDuration(self):
        return 500

env = {}
if (os.path.exists("/usr/local/bin/chmodtty9.sh")):
    env["DISPLAY"] = ":9"

bs.build(bs.DeqpBuilder(["gles2", "gles3"], env=env), time_limit=SlowTimeout())
        
