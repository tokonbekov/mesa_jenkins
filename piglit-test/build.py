#!/usr/bin/python

import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

class PiglitTester(object):
    def __init__(self):
        pass

    def test(self):
        br = bs.ProjectMap().build_root()
        o = bs.Options()

        libdir = "x86_64-linux-gnu"
        if o.arch == "m32":
            libdir = "i386-linux-gnu"
            
        env = { "LD_LIBRARY_PATH" : br + "/lib:" + \
                br + "/lib/" + libdir + ":" + \
                br + "/lib/dri:" + \
                br + "/lib/piglit/lib",

                "LIBGL_DRIVERS_PATH" : br + "/lib/dri",
                "GBM_DRIVERS_PATH" : br + "/lib/dri"
        }
        out_dir = br + "/test/" + o.hardware
        cmd = [br + "/bin/piglit",
               "run",
               "-p", "gbm",
               "-b", "junit",
               "quick",
               out_dir ]

        bs.run_batch_command(cmd, env=env)

        single_out_dir = br + "/../test"
        if not os.path.exists(single_out_dir):
            os.makedirs(single_out_dir)

        if os.path.exists(out_dir + "/results.xml"):
            # uniquely name all test files in one directory, for jenkins
            os.rename(out_dir + "/results.xml",
                      single_out_dir + "_".join(["/piglit-test",
                                                 o.hardware,
                                                 o.arch]) + ".xml")

        bs.Export().export()


    def build(self):
        pass

    def clean(self):
        pass

class SlowTimeout:
    def __init__(self):
        pass

    def GetDuration(self):
        return 120


bs.build(PiglitTester(), time_limit=SlowTimeout())
