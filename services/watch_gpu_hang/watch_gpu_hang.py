#!/usr/bin/python
import os
import sys
import time
import atexit
import fcntl
import errno
import signal

sys.path.append("/var/lib/git/mesa_jenkins/services/")
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
from daemon import Daemon

# This service is intended to be deployed on unstable systems where a
# hard GPU hang can occur within a single piglit run.  On systems which
# are more stable, the piglit test harness will detect GPU hang and
# schedule a reboot at the end of each test run.

# TLDR: don't enable this service except on non-production systems.


class GpuWatchDaemon(Daemon):
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        Daemon.__init__(self, pidfile, stdin, stdout, stderr)

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """
        f = open("/dev/kmsg", "r")
        fd = os.dup(f.fileno())
        f.close()
        fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
        while True:
            msg = ""
            try:
                msg = os.read(fd, 1024)
            except OSError as e:
                if e.errno == errno.EAGAIN:
                    time.sleep(5)
                else:
                    raise e
            if ("[drm] stuck on render ring" in msg or 
                "[drm] GPU crash" in msg or
                "[drm] GPU HANG" in msg):
                print "rebooting"
                os.system("reboot")
            else:
                print msg


if __name__ == "__main__":
    if len(sys.argv) == 2:
        
        daemon = GpuWatchDaemon('/var/run/watch_gpu_hang.pid', stdout="/var/log/watch_gpu_hang.log")
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
