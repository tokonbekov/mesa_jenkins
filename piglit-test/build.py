#!/usr/bin/python

import sys, os, argparse
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

class PiglitTester(object):
    def __init__(self, _piglit_test=None):
        self.piglit_test = _piglit_test

    def test(self):
        pm = bs.ProjectMap()
        br = pm.build_root()
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

        hardware_conf = o.hardware
        if "snb" in hardware_conf:
            hardware_conf = "snb"

        # all platforms other than g965 have separate 32-bit failures
        if o.hardware != "g965":
            if o.arch == "m32":
                hardware_conf = hardware_conf + "m32"
        hardware_conf = os.path.dirname(os.path.abspath(sys.argv[0])) + \
                        "/" + hardware_conf + ".conf"

        cmd = [br + "/bin/piglit",
               "run",
               "-p", "gbm",
               "-b", "junit",
               "-c",
               "--junit_suffix", "." + o.hardware + o.arch,
               "--config", hardware_conf,
               # hangs snb
               "--exclude-tests", "TRIANGLE_STRIP_ADJACENCY",
               # intermittently fails snb
               "--exclude-tests", "glsl-routing"]

        if self.piglit_test:
            # only use the last two components of test name, excluding
            # suffix
            test_name = ".".join(self.piglit_test.split(".")[-3:-1])
            cmd = cmd + ["--include-tests", test_name]
            
        cmd = cmd + ["quick",
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

        # create a copy of the test xml in the source root, where
        # jenkins can access it.
        cmd = ["cp", "-a", "-n",
               br + "/../test", pm.source_root()]
        bs.run_batch_command(cmd)

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

bs.build(PiglitTester(piglit_test), time_limit=SlowTimeout())
