#!/usr/bin/python

import git
import os
import signal
import subprocess
import sys
import time

sys.path.append("/var/lib/git/mesa_jenkins/services/")
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
from daemon import Daemon

sys.path.append("/var/lib/git/mesa_jenkins/")

_success = False
while not _success:
    try:
        _repo = git.Repo("/var/lib/git/mesa_jenkins")
        _repo.git.pull()
        _success = True
    except:
        print "Error: could not update buildsupport"
        time.sleep(10)

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "../.."))
import build_support as bs

sys.argv[0] = os.path.abspath(sys.argv[0])

try:
    bs.ProjectMap()
except(AssertionError):
    # if we are executing as a service, the script will not be within
    # a git source tree
    sys.argv[0] = "/var/lib/git/mesa_jenkins/services/fetch_mirrors/fetch_mesa_mirrors.py"

class TimeoutException(Exception):
    def __init__(self, msg):
        Exception.__init__(self)
        self._msg = msg

    def __str__(self):
        return self._msg

def signal_handler(signum, frame):
    raise TimeoutException("Fetch timed out.")

def signal_handler_quit(signum, frame):
    sys.exit(-1)


class RepoSyncer(Daemon):
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        Daemon.__init__(self, pidfile, stdin, stdout, stderr)

    def robust_clone(self, url, directory):
        success = False
        while not success:
            try:
                bs.run_batch_command(["git", "clone", "--mirror",
                                      url, directory])
                success = True
            except(subprocess.CalledProcessError):
                print "Error: could not clone " + url
                time.sleep(10)
        
    def run(self):
        signal.signal(signal.SIGALRM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler_quit)
        signal.signal(signal.SIGTERM, signal_handler_quit)

        while True:
            buildspec = bs.ProjectMap().build_spec()

            repo_dir = "/var/lib/git/"

            # build up a list of git repo objects for all known repos.  If the
            # origin or the remotes are not already cloned, clone them.
            repos = []
            repo_tags = buildspec.find("repos")
            for tag in repo_tags:
                url = tag.attrib["repo"]
                project = tag.tag
                origin_dir = repo_dir + project + "/origin"
                if not os.path.exists(origin_dir):
                    self.robust_clone(url, origin_dir)
                    bs.run_batch_command(["touch", origin_dir + "/git-daemon-export-ok"])
                repos.append(git.Repo(origin_dir))
                for a_remote in tag.findall("remote"):
                    remote_dir = repo_dir + project + "/" + a_remote.attrib["name"]
                    if not os.path.exists(remote_dir):
                        self.robust_clone(a_remote.attrib["repo"], remote_dir)
                        bs.run_batch_command(["touch", remote_dir + "/git-daemon-export-ok"])
                    repos.append(git.Repo(remote_dir))

            for repo in repos:
                try:
                    signal.alarm(300)   # 5 minutes
                    repo.git.fetch()
                    signal.alarm(0)
                except git.GitCommandError as e:
                    print "error fetching, ignoring: " + str(e)
                    signal.alarm(0)
                except AssertionError as e:
                    print "assertion while fetching: " + str(e)
                    signal.alarm(0)
                except TimeoutException as e:
                    print str(e)
                    signal.alarm(0)
            # pause a bit before fetching the next round
            time.sleep(20)


if __name__ == "__main__":
    if len(sys.argv) == 2:
        daemon = RepoSyncer('/var/run/fetch_mesa_mirrors.pid')
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
