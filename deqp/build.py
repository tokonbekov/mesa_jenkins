#!/usr/bin/python

import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

# todo: now that there is more than one component that needs
# to call mesa_version, it should be moved to a more sharable
# location
mesa_version = bs.PiglitTester().mesa_version()
if "10.5" in mesa_version or "10.6" in mesa_version:
    print "WARNING: deqp not supported on 10.6 and earlier."
    sys.exit(0)

bs.build(bs.CMakeBuilder(extra_definitions=["-DDEQP_TARGET=drm"]))
