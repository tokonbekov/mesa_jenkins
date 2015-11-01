#!/usr/bin/python

import os
import sys
import time
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

# HACK
# repeatedly invoking build() will overwrite the start times.  Record
# it now and write the correct value when the last build() has
# finished.  build() was not intended to be used this way.

start_time = time.time()

bs.build(bs.PiglitTester(_suite="cpu", device_override="byt"))
bs.build(bs.PiglitTester(_suite="cpu", device_override="g45"))
bs.build(bs.PiglitTester(_suite="cpu", device_override="g965"))
bs.build(bs.PiglitTester(_suite="cpu", device_override="ilk"))
bs.build(bs.PiglitTester(_suite="cpu", device_override="ivbgt2"))
bs.build(bs.PiglitTester(_suite="cpu", device_override="snbgt2"))
bs.build(bs.PiglitTester(_suite="cpu", device_override="hswgt3"))
bs.build(bs.PiglitTester(_suite="cpu", device_override="bdwgt2"))
bs.build(bs.PiglitTester(_suite="cpu", device_override="sklgt3"))
bs.build(bs.PiglitTester(_suite="cpu", device_override="bsw"))

options = bs.Options()
if (options.result_path):
    bs.ProjectInvoke(options).set_info("start_time", start_time)
