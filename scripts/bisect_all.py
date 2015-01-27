import os
import sys
import argparse
import xml.etree.ElementTree as ET
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

class Bisector:
    """tracks down bisections for a set of tests"""
    def __init__(self):
        # has a test list, a single range, and a base_revision to
        # check.
        self.target_tests = []
        self.bisect_project = None
        self.revision_range = []
        self.base_revisions = None

        # after bisect, this list grows
        self.generated_bisections = []

        # if bisect identifies a revision, this list grows.  Contains
        # PiglitTest objects
        self.bisected_tests = []
        self.bisected_revision = None

        
    def Bisect(self):
        """performs a bisection.  can generate more Bisector objects if tests
        split on the bisection."""
        pass
    

class BisectorSet:
    """Contains a set of Bisector objects.  Iterates on the set,
    appending new Bisector objects with subsets of tests when necessary"""
    #piglit_range, mesa_range, waffle_range, and drm_range.

    def __init__(self, tests, piglit_range, mesa_range,
                 waffle_range, drm_range):
        self._bisectors = []
        test_list = []
        for atest in tests:
            test_list.append(atest.test_name + ".all_platforms")
        test_arg = "--piglit_test=" + ",".join(test_list)

        revs = ["piglit-build="+piglit_range[-1].hexsha,
                "mesa="+mesa_range[0],
                "waffle="+waffle_range[0],
                "drm="+drm_range[0]]
        revspec = bs.RevisionSpecification(from_cmd_line=revs)
        hashstr = revspec.to_cmd_line_param().replace(" ", "_")
        out_dir = "/mnt/jenkins/results/bisect/" + hashstr
        j=bs.Jenkins(revspec, out_dir)

        o = bs.Options()
        o.result_path = out_dir
        depGraph = bs.DependencyGraph(["all-test"], o)
        j.build_all(depGraph, test_arg)


class PiglitTest:
    """Represents a single test.  Has the primary arch that will be
    tested, and a list of other arches that are expected to be caused
    by the same revision"""
    preferred_arches = ["m64", "m32"]
    preferred_platforms = ["hswgt3e", "hswgt2", "hswgt1", "ivbgt2",
                           "ivbgt1"] # ...

    def __init__(self, full_test_name, status):
        """full_test_name includes arch/platform.  status must be one
        of "pass", "fail", "crash" """

        arch_platform = full_test_name.split(".")[-1]
        arch = arch_platform[-3:]
        platform = arch_platform[:-3]
        if "gt" in platform:
            platform = platform[:3]

        self.test_name = ".".join(full_test_name.split(".")[:-1])
        self.arch = arch
        self.platform = platform
        self.other_arches = []
        self.status = status

    def AddTest(self, test):
        assert(test.test_name == self.test_name)
        assert(test.status == self.status)
        
        if self.arch == "m64" or test.arch == "m32":
            self.other_arches.append((test.arch, test.platform))
            return

        # m64 is preferred
        self.other_arches.append((self.arch, self.platform))
        self.arch = test.arch
        self.platform = test.platform

    def Print(self):
        print " ".join([self.test_name, self.arch, self.platform,
                        self.status, str(self.other_arches)])

class TestLister:
    """reads xml files and generates a set of PiglitTest objects"""
    def __init__(self, bad_dir):
        self._tests = {}
        # self.test_map is keyed by test name, value is PiglitTest
        for a_file in os.listdir(bad_dir):
            if "piglit-test" not in a_file:
                continue
            test_path = bad_dir + "/" + a_file
            self._add_tests(test_path)

    def _make_test(self, test_tag):

        full_test_name = test_tag.attrib["name"]
        full_test_name = test_tag.attrib["classname"] + "." + full_test_name
        full_test_name = full_test_name.replace("=", ".")
        full_test_name = full_test_name.replace(":", ".")
        full_test_name = full_test_name.replace(" ", ".")
        failnode = test_tag.find("./failure")
        if failnode is None:
            return PiglitTest(full_test_name, "crash")
        return PiglitTest(full_test_name, failnode.attrib["type"])        
            
    def _add_tests(self, test_path):
        t = ET.parse(test_path)
        r = t.getroot()

        for afail in r.findall(".//failure/..") + r.findall(".//error/.."):
            piglit_test = self._make_test(afail)
            
            if piglit_test.test_name not in self._tests:
                self._tests[piglit_test.test_name] = piglit_test
                continue
            self._tests[piglit_test.test_name].AddTest(piglit_test)

    def Print(self):
        for test in self._tests.values():
            test.Print()

    def Tests(self):
        return self._tests.values()

def get_commits(repo_name, good_revisions):
    target_repo = repos.repo(repo_name)
    commits = []
    for commit in target_repo.iter_commits(max_count=1000):
        commits.append(commit)
        if good_revisions[repo_name] in commit.hexsha:
            break
        print "    " + commit.hexsha
    return commits
    
parser = argparse.ArgumentParser(description="bisects everything")
parser.add_argument("--bad_rev", type=str)
parser.add_argument("--good_rev", type=str)
# instantiate test lister, generate PiglitTest objects

args = parser.parse_args(sys.argv[1:])

repos = bs.RepoSet()
repos.fetch()

_revspec = bs.RevisionSpecification(from_cmd_line=args.bad_rev.split())
_revspec.checkout()

_good_revisions = {}
for arev in args.good_rev.split():
    rev = arev.split("=")
    _good_revisions[rev[0]] = rev[1]

hash_str = _revspec.to_cmd_line_param().replace(" ", "_")
tl = TestLister("/mnt/jenkins/results/mesa_master/" +
                hash_str + "/daily/test/")

piglit_commits = get_commits("piglit-build", _good_revisions)
mesa_commits = get_commits("mesa", _good_revisions)
waffle_commits = get_commits("waffle", _good_revisions)
drm_commits = get_commits("drm", _good_revisions)

# create bisectorset with all the test objects
b = BisectorSet(tl.Tests(),
                piglit_range=piglit_commits, mesa_range=mesa_commits,
                waffle_range=waffle_commits, drm_range=drm_commits)
# run a build on first piglit rev, to identify which tests are from
# piglit.  make a list of bisector objects for them.

# repeat for mesa, waffle, drm

# 
