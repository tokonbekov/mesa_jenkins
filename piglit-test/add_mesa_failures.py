#!/usr/bin/python

import sys, os, argparse
current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.append(current_dir + "/..")
import build_support as bs

parser = argparse.ArgumentParser(description="bisects all mesa failures")
parser.add_argument("--bad_rev", type=str)
parser.add_argument("--good_rev", type=str)
args = parser.parse_args(sys.argv[1:])

repos = bs.RepoSet()
_revspec = bs.RevisionSpecification(from_cmd_line=args.bad_rev.split())
_revspec.checkout()

hash_str = _revspec.to_cmd_line_param().replace(" ", "_")
new_failures = bs.TestLister("/mnt/jenkins/results/mesa_master/" +
                             hash_str + "/daily/test/")

good_revisions = {}
for arev in args.good_rev.split():
    rev = arev.split("=")
    good_revisions[rev[0]] = rev[1]

mesa_commits = []
mesa_repo = repos.repo("mesa")

print "mesa revisions under bisection:"
for commit in mesa_repo.iter_commits(max_count=1000):
    mesa_commits.append(commit)
    print commit.hexsha
    if good_revisions["mesa"] in commit.hexsha:
        break

revspec = bs.RevisionSpecification(from_cmd_line=["mesa=" + mesa_commits[-1].hexsha])
revspec.checkout()
revspec = bs.RevisionSpecification()
hashstr = revspec.to_cmd_line_param().replace(" ", "_")
spec_xml = bs.ProjectMap().build_spec()
results_dir = spec_xml.find("build_master").attrib["results_dir"]
out_dir = "/".join([results_dir, "bisect", hashstr])

j=bs.Jenkins(revspec, out_dir)
o = bs.Options(["bisect_all.py"])
o.result_path = out_dir
depGraph = bs.DependencyGraph(["piglit-gpu-all"], o)
print "Building old mesa to: " + out_dir

test_list = []
for atest in new_failures.Tests():
    test_list.append(atest.test_name + ".all_platforms")
test_arg = "--piglit_test=" + ",".join(test_list)


j.build_all(depGraph, extra_arg=test_arg, print_summary=False)
tl = bs.TestLister(out_dir + "/test/")
print "failures due to mesa:"
mesa_failures = new_failures.TestsNotIn(tl)
for a_test in mesa_failures:
    a_test.Print()

for a_test in mesa_failures:
    a_test.Bisect("mesa-build", mesa_commits)
    a_test.UpdateConf(current_dir)

