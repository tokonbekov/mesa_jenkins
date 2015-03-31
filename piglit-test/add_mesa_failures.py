#!/usr/bin/python

import sys, os, argparse, re
current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.append(current_dir + "/..")
import build_support as bs

parser = argparse.ArgumentParser(description="bisects all mesa failures")
parser.add_argument("--test_dir", type=str)
parser.add_argument("--good_rev", type=str)
args = parser.parse_args(sys.argv[1:])

# get revisions from out directory
dirnames = os.path.abspath(args.test_dir).split("/")
if dirnames[-1] != "test":
    args.test_dir = args.test_dir + "/test"
    dirnames = os.path.abspath(args.test_dir).split("/")
hash_dir = dirnames[5]
revs = hash_dir.split("_")

spec_xml = bs.ProjectMap().build_spec()
results_dir = spec_xml.find("build_master").attrib["results_dir"]

repos = bs.RepoSet()
_revspec = bs.RevisionSpecification(from_cmd_line=revs)
_revspec.checkout()

def make_test_list(testlister):
    _test_list = []
    for atest in testlister.Tests():
        test_name_good_chars = re.sub('[_ !:=]', ".", atest.test_name)
        _test_list.append(test_name_good_chars + ".all_platforms")
    return "--piglit_test=" + ",".join(_test_list)

new_failures = bs.TestLister(args.test_dir)
test_arg = make_test_list(new_failures)

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

# retest build, in case expected failures has been updated
# copy build root to bisect directory
bisect_dir = results_dir + "/bisect/" + hash_dir
cmd = ["rsync", "-rlptD", "/".join(dirnames[:-1]) +"/", bisect_dir]
bs.run_batch_command(cmd)
bs.rmtree(bisect_dir + "/test")
bs.rmtree(bisect_dir + "/piglit-test")

j=bs.Jenkins(_revspec, bisect_dir)
o = bs.Options(["bisect_all.py"])
o.result_path = bisect_dir
depGraph = bs.DependencyGraph(["piglit-gpu-all"], o)
print "Retesting mesa to: " + bisect_dir
j.build_all(depGraph, extra_arg=test_arg, print_summary=False)
new_failures = bs.TestLister(bisect_dir + "/test/")

if not new_failures.Tests():
    print "All tests fixed"
    sys.exit(0)

test_arg = make_test_list(new_failures)

# build old mesa to see what mesa regressions were
revspec = bs.RevisionSpecification(from_cmd_line=["mesa=" + mesa_commits[-1].hexsha])
revspec.checkout()
revspec = bs.RevisionSpecification()
hashstr = revspec.to_cmd_line_param().replace(" ", "_")
old_out_dir = "/".join([results_dir, "bisect", hashstr])
bs.rmtree(old_out_dir + "/test")
bs.rmtree(old_out_dir + "/piglit-test")

j=bs.Jenkins(revspec, old_out_dir)
o = bs.Options(["bisect_all.py"])
o.result_path = old_out_dir
depGraph = bs.DependencyGraph(["piglit-gpu-all"], o)
print "Building old mesa to: " + old_out_dir

j.build_all(depGraph, extra_arg=test_arg, print_summary=False)
tl = bs.TestLister(old_out_dir + "/test/")
print "failures due to mesa:"
mesa_failures = new_failures.TestsNotIn(tl)
for a_test in mesa_failures:
    a_test.Print()

for a_test in mesa_failures:
    a_test.Bisect("mesa", mesa_commits)
    a_test.UpdateConf()

