import git
import hashlib
import os
import sys
import time
import urllib2

# When running as a service, mesa_jenkins must be available to
# automation.  See:
# https://github.com/janesma/mesa_jenkins/wiki/services-setup

# this service triggers builds based on commits made to repos as set
# in the build_specification.xml at
# build_specification/branches/branch tags.

# append services directory to pythonpath, so we can make use of
# Daemon.  Second line is for finding Daemon when running from the
# checkout, and not when runnning as a service.
sys.path.append("/var/lib/git/mesa_jenkins/services/")
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
from daemon import Daemon

# append build_support directory to pythonpath, so we can make use of
# RepoSet etc.  Second line is for finding build_support when running
# from the checkout, and not when runnning as a service.
sys.path.append("/var/lib/git/mesa_jenkins/")
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "../.."))
import build_support as bs




class Poller(Daemon):
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        Daemon.__init__(self, pidfile, stdin, stdout, stderr)
    
    def file_checksum(self, fname):
        return hashlib.md5(open(fname, 'rb').read()).digest()

    def run(self):
        # running a service through intel's proxy requires some
        # annoying settings.
        os.environ["GIT_PYTHON_GIT_EXECUTABLE"] = "/usr/local/bin/git"
        # without this, git-remote-https spins at 100%
        os.environ["http_proxy"] = "http://proxy.jf.intel.com:911/"
        os.environ["https_proxy"] = "http://proxy.jf.intel.com:911/"
        try:
            bs.ProjectMap()
        except:
            sys.argv[0] = "/var/lib/git/mesa_jenkins/foo.py"
        pm = bs.ProjectMap()
        spec_file = pm.source_root() + "/build_specification.xml"

        new_spec_hash = None
        while True:
            orig_spec_hash = self.file_checksum(spec_file)
            spec = pm.build_spec()
            server = spec.find("build_master").attrib["host"]
            if new_spec_hash is not None:
                print "Build Specification updated"
            new_spec_hash = self.file_checksum(spec_file)
            status = bs.RepoStatus()
            while new_spec_hash == orig_spec_hash:
                branches = status.poll()
                for (branch, commit) in branches.iteritems():
                    print "Building " + branch
                    job_url = "http://" + server + "/job/" + branch + \
                              "/buildWithParameters?token=xyzzy&name=" + commit + "&type=percheckin"
                    retry_count = 0
                    while retry_count < 10:
                        try:
                            #f = urllib2.urlopen(job_url)
                            #f.read()
                            print job_url
                            break
                        except urllib2.HTTPError as e:
                            print e
                            retry_count = retry_count + 1
                            print "ERROR: failed to reach jenkins, retrying: " + job_url
                            time.sleep(10)

                new_spec_hash = self.file_checksum(spec_file)

if __name__ == "__main__":
    if len(sys.argv) == 2:
        daemon =  Poller('/var/run/poll_branches.pid', stderr="/var/log/poll_mesa_branches.log")
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
