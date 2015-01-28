import os
import sys
import argparse
import xml.etree.ElementTree as ET
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

class ProjectBisector:
    """tracks down bisections for a set of tests"""
    def __init__(self, project, target_tests, revisions):
        # has a test list, a single range, and a base_revision to
        # check.
        self.bisect_project = project
        self.target_tests = target_tests
        self.revision_range = revisions

        # save the current revisions as a starting point
        self.revspec = bs.RevisionSpecification()
        
        # when bisect identifies a revision, this dict grows.  values
        # are test names
        self.bisected_revisions = {}
        
    def Bisect(self):
        """performs bisections for each test on the project"""
        for a_piglit_test in self.target_tests:
            self.revspec.checkout()
            bisector = bs.Bisector("piglit-test", a_piglit_test.test_name,
                                   a_piglit_test.arch,
                                   a_piglit_test.hardware,
                                   self.revision_range)
            first_failure = bisector.Bisect()
            if first_failure not in self.bisected_revisions:
                self.bisected_revisions[first_failure] = []
            self.bisected_revisions[first_failure].append(a_piglit_test.test_name)

    def Print(self):
        print "Project: " + self.bisect_project
        for (a_rev, test_list) in self.bisected_revisions.items():
            print "\tRevision: " + a_rev
            for a_test in test_list:
                print "\t\tTest: " + a_test.Print()
            
        
class BisectorSet:
    """Contains a set of Bisector objects.  Iterates on the set,
    appending new Bisector objects with subsets of tests when necessary"""
    #piglit_range, mesa_range, waffle_range, and drm_range.

    def __init__(self, all_test_list, piglit_range, mesa_range,
                 waffle_range, drm_range):
        self._bisectors = []
        test_list = []
        for atest in all_test_list.Tests():
            test_list.append(atest.test_name + ".all_platforms")
        test_arg = "--piglit_test=" + ",".join(test_list)

        revs = ["piglit-build="+piglit_range[-1].hexsha,
                "mesa="+mesa_range[0].hexsha,
                "waffle="+waffle_range[0].hexsha,
                "drm="+drm_range[0].hexsha]
        revspec = bs.RevisionSpecification(from_cmd_line=revs)
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
        j.build_all(depGraph, extra_arg=test_arg, print_summary=False)

        # any test not in this list will be a result of piglit
        tl = TestLister(out_dir + "/test/")
        print "piglit"
        for a_test in all_test_list.TestsNotIn(tl):
            a_test.Print()
        self._bisectors.append(ProjectBisector("piglit-build",
                                               all_test_list.TestsNotIn(tl),
                                               piglit_range))

        revs = ["piglit-build="+piglit_range[0].hexsha,
                "mesa="+mesa_range[-1].hexsha,
                "waffle="+waffle_range[0].hexsha,
                "drm="+drm_range[0].hexsha]
        revspec = bs.RevisionSpecification(from_cmd_line=revs)
        revspec.checkout()
        revspec = bs.RevisionSpecification()
        hashstr = revspec.to_cmd_line_param().replace(" ", "_")
        out_dir = "/mnt/jenkins/results/bisect/" + hashstr
        j=bs.Jenkins(revspec, out_dir)

        o = bs.Options(["bisect_all.py"])
        o.result_path = out_dir
        depGraph = bs.DependencyGraph(["piglit-gpu-all"], o)
        j.build_all(depGraph, extra_arg=test_arg, print_summary=False)

        # any test not in this list will be a result of mesa
        tl = TestLister(out_dir + "/test/")
        print "mesa"
        for a_test in all_test_list.TestsNotIn(tl):
            a_test.Print()
        self._bisectors.append(ProjectBisector("mesa",
                                               all_test_list.TestsNotIn(tl),
                                               mesa_range))

        revs = ["piglit-build="+piglit_range[0].hexsha,
                "mesa="+mesa_range[0].hexsha,
                "waffle="+waffle_range[-1].hexsha,
                "drm="+drm_range[0].hexsha]
        revspec = bs.RevisionSpecification(from_cmd_line=revs)
        revspec.checkout()
        revspec = bs.RevisionSpecification()
        hashstr = revspec.to_cmd_line_param().replace(" ", "_")
        out_dir = "/mnt/jenkins/results/bisect/" + hashstr
        j=bs.Jenkins(revspec, out_dir)

        o = bs.Options(["bisect_all.py"])
        o.result_path = out_dir
        depGraph = bs.DependencyGraph(["piglit-gpu-all"], o)
        j.build_all(depGraph, extra_arg=test_arg, print_summary=False)

        # any test not in this list will be a result of waffle
        tl = TestLister(out_dir + "/test/")
        print "waffle"
        for a_test in all_test_list.TestsNotIn(tl):
            a_test.Print()
        self._bisectors.append(ProjectBisector("waffle",
                                               all_test_list.TestsNotIn(tl),
                                               waffle_range))

        revs = ["piglit-build="+piglit_range[0].hexsha,
                "mesa="+mesa_range[0].hexsha,
                "waffle="+waffle_range[0].hexsha,
                "drm="+drm_range[-1].hexsha]
        revspec = bs.RevisionSpecification(from_cmd_line=revs)
        revspec.checkout()
        revspec = bs.RevisionSpecification()
        hashstr = revspec.to_cmd_line_param().replace(" ", "_")
        out_dir = "/mnt/jenkins/results/bisect/" + hashstr
        j=bs.Jenkins(revspec, out_dir)

        o = bs.Options(["bisect_all.py"])
        o.result_path = out_dir
        depGraph = bs.DependencyGraph(["piglit-gpu-all"], o)
        j.build_all(depGraph, extra_arg=test_arg, print_summary=False)
        
        # any test not in this list will be a result of drm
        tl = TestLister(out_dir + "/test/")
        print "drm"
        for a_test in all_test_list.TestsNotIn(tl):
            a_test.Print()
        self._bisectors.append(ProjectBisector("drm",
                                               all_test_list.TestsNotIn(tl),
                                               drm_range))

    def Bisect(self):
        for a_project in self._bisectors:
            a_project.Bisect()
        
    def Print(self):
        for a_project in self._bisectors:
            a_project.Print()

class PiglitTest:
    """Represents a single test.  Has the primary arch that will be
    tested, and a list of other arches that are expected to be caused by
    the same revision"""
    preferred_arches = ["m64", "m32"]
    preferred_hardware = ["hswgt3e", "hswgt2", "hswgt1", "ivbgt2",
                          "ivbgt1"] # ...

    def __init__(self, full_test_name, status):
        """full_test_name includes arch/platform.  status must be one
        of "pass", "fail", "crash" """

        arch_hardware = full_test_name.split(".")[-1]
        arch = arch_hardware[-3:]
        hardware = arch_hardware[:-3]
        if "gt" in hardware:
            hardware = hardware[:3]

        self.test_name = ".".join(full_test_name.split(".")[:-1])
        self.arch = arch
        self.hardware = hardware
        self.other_arches = []
        self.status = status

    def AddTest(self, test):
        assert(test.test_name == self.test_name)
        assert(test.status == self.status)
        
        if self.arch == "m64" or test.arch == "m32":
            self.other_arches.append((test.arch, test.hardware))
            return

        # m64 is preferred
        self.other_arches.append((self.arch, self.hardware))
        self.arch = test.arch
        self.hardware = test.hardware

    def Print(self):
        print " ".join([self.test_name, self.arch, self.hardware,
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
        full_test_name = full_test_name.replace("!", ".")
        full_test_name = full_test_name.replace("_", ".")
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

    def TestsNotIn(self, other_test_list):
        out_list = []
        for (name, test) in self._tests.items():
            if name not in other_test_list._tests:
                out_list.append(test)
        return out_list

def get_commits(repo_name, good_revisions):
    target_repo = repos.repo(repo_name)
    commits = []
    for commit in target_repo.iter_commits(max_count=1000):
        commits.append(commit)
        if good_revisions[repo_name] in commit.hexsha:
            break
    return commits
    
parser = argparse.ArgumentParser(description="bisects everything")
parser.add_argument("--bad_rev", type=str)
parser.add_argument("--good_rev", type=str)
# instantiate test lister, generate PiglitTest objects

args = parser.parse_args(sys.argv[1:])

repos = bs.RepoSet()
#repos.fetch()

_revspec = bs.RevisionSpecification(from_cmd_line=args.bad_rev.split())
_revspec.checkout()

_good_revisions = {}
for arev in args.good_rev.split():
    rev = arev.split("=")
    _good_revisions[rev[0]] = rev[1]

hash_str = _revspec.to_cmd_line_param().replace(" ", "_")
_tl = TestLister("/mnt/jenkins/results/mesa_master/" +
                hash_str + "/daily/test/")

piglit_commits = get_commits("piglit-build", _good_revisions)
mesa_commits = get_commits("mesa", _good_revisions)
waffle_commits = get_commits("waffle", _good_revisions)
drm_commits = get_commits("drm", _good_revisions)

# create bisectorset with all the test objects
b = BisectorSet(_tl,
                piglit_range=piglit_commits, mesa_range=mesa_commits,
                waffle_range=waffle_commits, drm_range=drm_commits)

b.Bisect()
b.Print()
