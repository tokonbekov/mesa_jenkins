#!/usr/bin/python

import sys, os, argparse, re
current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.append(current_dir + "/..")
import build_support as bs

parser = argparse.ArgumentParser(description="bisects all piglit failures")
parser.add_argument("--result_path", type=str)
parser.add_argument("--good_rev", type=str)
parser.add_argument('--to', metavar='to', type=str, default="",
                    help='send resulting patch to this email')
args = parser.parse_args(sys.argv[1:])

# get revisions from out directory
test_dir = os.path.abspath(args.result_path + "/test")
if not os.path.exists(test_dir):
    print "ERROR: no tests in --result_path: " + test_dir
    sys.exit(-1)

dirnames = os.path.abspath(test_dir).split("/")
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

new_failures = bs.TestLister(test_dir)
test_arg = make_test_list(new_failures)

good_revisions = {}
# accept either a single rev or a revision hash
for arev in args.good_rev.split():
    if "=" not in arev:
        good_revisions["piglit"] = arev
        continue
    rev = arev.split("=")
    good_revisions[rev[0]] = rev[1]

piglit_commits = []
piglit_repo = repos.repo("piglit")

print "Piglit revisions under bisection:"
for commit in piglit_repo.iter_commits(max_count=1000):
    piglit_commits.append(commit)
    print commit.hexsha
    if good_revisions["piglit"] in commit.hexsha:
        break

# retest build, in case expected failures has been updated
# copy build root to bisect directory
bisect_dir = results_dir + "/bisect/" + hash_dir
cmd = ["rsync", "-rlptD", "/".join(dirnames[:-1]) +"/", bisect_dir]
bs.run_batch_command(cmd)
bs.rmtree(bisect_dir + "/test")
bs.rmtree(bisect_dir + "/piglit-test")
bs.rmtree(old_out_dir + "/piglit-nir-test")

j=bs.Jenkins(_revspec, bisect_dir)
o = bs.Options(["bisect_all.py"])
o.result_path = bisect_dir
depGraph = bs.DependencyGraph(["piglit-gpu-all"], o)
print "Retesting piglit to: " + bisect_dir
j.build_all(depGraph, extra_arg=test_arg, print_summary=False)
new_failures = bs.TestLister(bisect_dir + "/test/")

if not new_failures.Tests():
    print "All tests fixed"
    sys.exit(0)

test_arg = make_test_list(new_failures)

# build old piglit to see what piglit regressions were
revspec = bs.RevisionSpecification(from_cmd_line=["piglit=" + piglit_commits[-1].hexsha])
revspec.checkout()
revspec = bs.RevisionSpecification()
hashstr = revspec.to_cmd_line_param().replace(" ", "_")
old_out_dir = "/".join([results_dir, "bisect", hashstr])
bs.rmtree(old_out_dir + "/test")
bs.rmtree(old_out_dir + "/piglit-test")
bs.rmtree(old_out_dir + "/piglit-nir-test")

j=bs.Jenkins(revspec, old_out_dir)
o = bs.Options(["bisect_all.py"])
o.result_path = old_out_dir
depGraph = bs.DependencyGraph(["piglit-gpu-all"], o)
print "Building old piglit to: " + old_out_dir

j.build_all(depGraph, extra_arg=test_arg, print_summary=False)
tl = bs.TestLister(old_out_dir + "/test/")
print "failures due to piglit:"
piglit_failures = new_failures.TestsNotIn(tl)
for a_test in piglit_failures:
    a_test.Print()

for a_test in piglit_failures:
    a_test.Bisect("piglit-test", piglit_commits)
    a_test.UpdateConf()

if args.to:
    patch_text = git.Repo().git.diff()
    msg = MIMEText(patch_text)
    msg["Subject"] = "[PATCH] jenkins updates due to bisect of piglit"
    msg["From"] = "Do Not Reply <mesa_jenkins@intel.com>"
    msg["To"] = args.to
    s = smtplib.SMTP('or-out.intel.com')
    to = args.to.split(",")
    s.sendmail(msg["From"], to, msg.as_string())
