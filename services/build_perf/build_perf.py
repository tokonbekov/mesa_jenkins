#!/usr/bin/python2

from __future__ import print_function
import ast
import os
import time
import urllib2

# When running as a service, mesa_jenkins must be available to
# automation.  See:
# https://github.com/janesma/mesa_jenkins/wiki/services-setup

# this service triggers builds based on commits made to repos as set
# in the build_specification.xml at
# build_specification/branches/branch tags.

def write_pid(pidfile):
    """Write the PID file."""
    with open(pidfile, 'w') as f:
        f.write(str(os.getpid()))


def main():
    try:
        write_pid('/var/run/build_perf.pid')
    except:
        pass
    master_url = "http://otc-mesa-ci.jf.intel.com/computer/%28master%29/api/python"
    perf_url = "http://otc-mesa-ci.jf.intel.com/view/All/job/perf/buildWithParameters?token=xyzzy"

    while True:
        try:
            f = urllib2.urlopen(master_url)
            master_page = ast.literal_eval(f.read())
            if master_page["idle"]:
                f = urllib2.urlopen(perf_url)
                f.read()
        except:
            time.sleep(10)
            continue

        time.sleep(60)

if __name__ == "__main__":
    main()
