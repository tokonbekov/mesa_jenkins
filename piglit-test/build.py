#!/usr/bin/python

import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

class PiglitTester(object):
    def __init__(self):
        pass

    def test(self):
        br = bs.ProjectMap().build_root()
        env = { "LD_LIBRARY_PATH" : br + "/lib:" + \
                br + "/lib/x86_64-linux-gnu:" + \
                br + "/lib/dri:" + \
                br + "/lib/piglit/lib",

                "LIBGL_DRIVERS_PATH" : br + "/lib/dri",
                "GBM_DRIVERS_PATH" : br + "/lib/dri"
        }
        o = bs.Options()
        out_dir = br + "/test/" + o.hardware
        cmd = [br + "/bin/piglit",
               "run",
               "-p", "gbm",
               "-b", "junit",
               "quick",
               out_dir ]

        if os.path.exists(out_dir + "/results.xml"):
            os.rename(out_dir + "/results.xml",
                      out_dir + "/piglit-test.xml")

        bs.run_batch_command(cmd, env=env)
        bs.Export().export()


    def build(self):
        pass

    def clean(self):
        pass


bs.build(PiglitTester())
