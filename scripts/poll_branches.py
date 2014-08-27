import sys, os, urllib2, time
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

status = bs.RepoStatus()

pm = bs.ProjectMap()
spec = pm.build_spec()
server = spec.find("build_master").attrib["host"]
while True:
    branches = status.poll()
    for (branch, commit) in branches.iteritems():
        print "Building " + branch
        job_url = "http://" + server + "/job/" + branch + \
                  "/buildWithParameters?name=" + commit
        f = urllib2.urlopen(job_url)
        f.read()

    time.sleep(60)
