#!/usr/bin/python

import git
import argparse
import sys
import urllib
import urllib2
import time

parser = argparse.ArgumentParser(description="builds a sequence of commits on jenkins")

parser.add_argument('--start_rev', type=str, default='',
                    help="The sha starting the sequence to be tested")

parser.add_argument('--end_rev', type=str, default='',
                    help="The sha ending the sequence to be tested")

parser.add_argument('--repo', type=str, default='.',
                    help="The mesa repository to use for calculating the revision sequence")

parser.add_argument('--series_name', type=str, default='',
                    help="The name to apply to each custom build")

args = parser.parse_args(sys.argv[1:])

if not args.series_name:
    print "ERROR: --series_name required"
    sys.exit(-1)

try:
    repo = git.Repo(args.repo)
except:
    print "ERROR: mesa repository not found.  Please provide --repo"
    sys.exit(-1)

try:
    repo.git.checkout(args.end_rev)
except:
    print "ERROR: could not check out end_rev: " + args.end_rev + ". Please provide --end_rev"
    sys.exit(-1)

commits = []
for commit in repo.iter_commits(max_count=1000):
    commits.append(commit)
    if args.start_rev in commit.hexsha:
        break

if args.start_rev not in commits[-1].hexsha:
    print "ERROR: could not find start_rev: " + args.start_rev + ". Please provide --start_rev"

print "building series:"
for commit in commits:
    print commit.hexsha

    custom_url = "http://otc-gfxtest-01.jf.intel.com/job/mesa_custom/buildWithParameters?token=xyzzy&{0}"
    job_args = { "name" : args.series_name,
                 "revision" : "mesa=" + commit.hexsha }
    url = custom_url.format(urllib.urlencode(job_args))

    failcount = 0
    while True:
        try:
            f = urllib2.urlopen(url)
            break
        except (urllib2.HTTPError, urllib2.URLError):
            print "failure urllib2.urlopen(\"{0}\")".format(url)
            failcount += 1
            if failcount == 5:
                raise
            time.sleep(5)

