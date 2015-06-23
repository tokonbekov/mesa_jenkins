import re
import os
import time
import xml.etree.ElementTree as ET
import ConfigParser

from . import RevisionSpecification
from . import Options
from . import ProjectMap
from . import rmtree
from . import Jenkins
from . import DependencyGraph
from . import ProjectInvoke
from . import BuildFailure


class NoConfigFile(Exception):
    pass


def get_conf_file(hardware, arch, project="piglit-test"):
    # strip the gtX strings off of the hardware, because there are
    # no examples where a sku has a different config
    if "gt" in hardware:
        hardware = hardware[:3]
    conf_dir = ProjectMap().source_root() + "/" + project + "/"
    conf_file = conf_dir + "/" + hardware + arch + ".conf"
    if not os.path.exists(conf_file):
        conf_file = conf_dir + "/" + hardware + ".conf"

    if not os.path.exists(conf_file):
        raise NoConfigFile
    return conf_file

class Bisector:
    def __init__(self, bisect_project, test,
                 commits, retest_path):
        self.project = bisect_project
        self.test = test
        # remove inadvertent whitespace, which is easy to add when
        # triggering builds on jenkins
        self.test_name = test.test_name.strip()
        self.arch = test.arch
        self.hardware = test.hardware
        self.commits = commits
        self.last_failure = None
        self._retest_path=retest_path

    def Bisect(self):
        if not self.commits:
            return
        current_build = len(self.commits) / 2
        repo_project = self.project
        if "piglit" in repo_project:
            repo_project = "piglit"
        rev = repo_project + "=" + self.commits[current_build].hexsha
        print "Range: " + self.commits[0].hexsha + " - " + self.commits[-1].hexsha + " (" + str(len(self.commits)) + ")"
        print "Building revision: " + rev

        o = Options(args=["ignore"])
        o.type = "developer"
        o.config = "debug"
        o.arch = self.arch
        o.hardware = self.hardware
        o.action = ["build", "test"]

        print "Bisector Bisect checking out: " + rev
        revspec = RevisionSpecification(from_cmd_line=[rev])
        revspec.checkout()
        revspec = RevisionSpecification()
        hashstr = revspec.to_cmd_line_param().replace(" ", "_")
        spec_xml = ProjectMap().build_spec()
        results_dir = spec_xml.find("build_master").attrib["results_dir"]
        result_path = "/".join([results_dir, "bisect", hashstr])
        o.result_path = result_path
        o.retest_path = self._retest_path

        # if retest_path == result_path, then we don't have to build.
        # This will occur when bisect has reached the most recent
        # revision.  The newest revision was already
        # built/tested. before beginning the bisect.
        if (o.result_path != o.retest_path):
            rmtree(result_path + "/test")

            global jen
            jen = Jenkins(result_path=result_path,
                          revspec=revspec)

            depGraph = DependencyGraph(self.test.project, o)
            # remove test build from graph, because we always want to build
            # it.
            bi = ProjectInvoke(project=self.test.project, 
                               options=o)
            bi.set_info("status", "bisect-rebuild")

            depGraph.build_complete(bi)
            try:
                jen.build_all(depGraph, "bisect", print_summary=False)
                print "Starting: " + bi.to_short_string()
                jen.build(bi, branch="mesa_master")
                jen.wait_for_build()
            except BuildFailure:
                print "BUILD FAILED - exception: " + rev
                if current_build + 1 == len(self.commits):
                    print "FIRST DETECTED FAILURE: " + rev
                    return rev
                self.last_failure = rev
                self.commits = self.commits[current_build+1:]
                return self.Bisect()

        if self.test.Passed(result_path, rev):
            if current_build == 0:
                print "LAST DETECTED SUCCESS: " + rev
                return self.last_failure
            self.commits = self.commits[:current_build]
            return self.Bisect()
        else:
            # test failed
            if current_build + 1 == len(self.commits):
                print "FIRST DETECTED FAILURE: " + rev
                return rev
            self.last_failure = rev
            self.commits = self.commits[current_build + 1:]
            return self.Bisect()


# needed to preserve case in the options
class CaseConfig(ConfigParser.SafeConfigParser):
    def optionxform(self, optionstr):
        return optionstr

class PiglitTest:
    """Represents a single test.  Has the primary arch that will be
    tested, and a list of other arches that are expected to be caused by
    the same revision"""
    preferred_arches = ["m64", "m32"]
    preferred_hardware = ["hsw", "ivb", "hswgt3e", "hswgt2", "hswgt1", "ivbgt2",
                          "ivbgt1"] # ...

    def __init__(self, full_test_name, status, test_tag=None, retest_path=""):
        """full_test_name includes arch/platform.  status must be one
        of "pass", "fail", "crash" """
        self.command_line = ""
        if test_tag is not None:
            full_test_name = test_tag.attrib["name"]
            full_test_name = test_tag.attrib["classname"] + "." + full_test_name
            full_test_name = full_test_name.replace("=", ".")
            full_test_name = full_test_name.replace(":", ".")
            failnode = test_tag.find("./failure")
            if failnode is not None:
                # assume fail type is crash if the type attribute doesn't exist
                status = failnode.attrib.get("type", "crash")
            else:
                status = "crash"
            system_out_node = test_tag.find("./system-out")

            if system_out_node is not None:
                self.command_line = system_out_node.text.splitlines()[0]
                
        self._retest_path = retest_path
        arch_hardware = full_test_name.split(".")[-1]
        arch = arch_hardware[-3:]
        hardware = arch_hardware[:-3]
        self.project = "piglit-test"
        if "piglit.deqp" in full_test_name.lower():
            self.project = "deqp-test"
        if "gt" in hardware:
            hardware = hardware[:3]

        self.test_name = ".".join(full_test_name.split(".")[:-1])
        self.arch = arch
        self.hardware = hardware
        self.other_arches = []
        self.status = status
        self.bisected_revision = "unknown"

    def AddTest(self, test):
        assert(test.test_name == self.test_name)
        if (test.status != self.status):
            print "WARNING: test status mismatch: " + self.test_name
            return

        primary_arch = self.arch
        primary_hw = self.hardware
        secondary_arch = test.arch
        secondary_hw = test.hardware

        if self.arch == "m32" and test.arch == "m64":
            # m64 is preferred
            primary_arch = test.arch
            primary_hw = test.hardware
            secondary_arch = self.arch
            secondary_hw = self.hardware
        elif (self.hardware not in PiglitTest.preferred_hardware and 
              test.hardware in PiglitTest.preferred_hardware):
            # else prefer faster platform
            primary_arch = test.arch
            primary_hw = test.hardware
            secondary_arch = self.arch
            secondary_hw = self.hardware
        
        self.other_arches.append((secondary_arch, secondary_hw))
        self.arch = primary_arch
        self.hardware = primary_hw

    def Print(self):
        print " ".join([self.project, self.test_name, self.arch, self.hardware,
                        self.status, str(self.other_arches)])

    def PrettyPrint(self, fh):
        fh.write("Project: " + self.project + "\n"
                 "Test: " + self.test_name + "\n"
                 "Status: " + self.status + "\n"
                 "Platform/arch:\n\t"+ self.hardware + "/" + self.arch)
        for arch, hw in self.other_arches:
            fh.write(", " + hw + "/" + arch)
        fh.write("\nCommand line: " + self.command_line + "\n\n")

    def Bisect(self, bisect_project, commits):
        print "Bisecting for " + self.test_name
        b = Bisector(bisect_project, self, 
                     commits, self._retest_path)
        self.bisected_revision = b.Bisect()
        if not self.bisected_revision:
            print "No bisection found for " + self.test_name
            return
        self.bisected_revision = self.bisected_revision.replace("=", " ")

    def GetConf(self, hardware=None, arch=None):
        if not hardware:
            hardware = self.hardware
        if not arch:
            arch = self.arch
        return get_conf_file(hardware, arch, project=self.project)
        
    def UpdateConf(self):
        if not self.bisected_revision:
            return
        full_list = [(self.arch, self.hardware)] + self.other_arches
        for arch, hardware in full_list:
            if "gt" in hardware:
                hardware = hardware[:3]
            try:
                conf_file = self.GetConf(hardware=hardware, arch=arch)
            except NoConfigFile:
                continue
            c = CaseConfig(allow_no_value=True)
            c.optionxform = str
            c.read(conf_file)

            # remove test from whatever section it might be in, and
            # add it back to the right place
            c.remove_option("expected-failures", self.test_name)
            c.remove_option("expected-crashes", self.test_name)
            if self.status == "fail":
                c.set("expected-failures", self.test_name, self.bisected_revision)
            elif self.status == "crash":
                c.set("expected-crashes", self.test_name, self.bisected_revision)
            elif self.status == "pass":
                if not c.has_section("fixed-tests"):
                    c.add_section("fixed-tests")
                c.set("fixed-tests", self.test_name, self.bisected_revision)
            else:
                print conf_file + ": removed " + self.test_name

            c.write(open(conf_file, "w"))

    def GetConfRevision(self):
        hardware = self.hardware
        if "gt" in hardware:
            hardware = hardware[:3]
        try:
            conf_file = self.GetConf()
        except NoConfigFile:
            return ''

        c = CaseConfig(allow_no_value=True)
        c.optionxform = str
        c.read(conf_file)
        for section in ["expected-failures", "expected-crashes", "fixed-tests"]:
            try:
                rev = c.get(section, self.test_name)
                if not rev:
                    rev = ""
                return rev
            except(ConfigParser.NoSectionError, ConfigParser.NoOptionError):
                pass
        return ""

    def Passed(self, result_path, rev):
        # returns true if the piglit test passed at the specified result_path
        test_result = "/".join([result_path, "test", self.project + "_" +
                                self.hardware + "_" + self.arch + ".xml"])
        iteration = 0
        while not os.path.exists(test_result):
            if iteration < 40:
                time.sleep(1)
                iteration = iteration + 1
                continue
            print "BUILD FAILED - no test results: " + test_result
            return False

        result = ET.parse(test_result)
        for testcase in result.findall("./testsuite/testcase"):
            testname = testcase.attrib["classname"] + "." + testcase.attrib["name"]
            #strip off the arch/platform and drop the special characters
            testname = ".".join(testname.split(".")[:-1])
            testname = re.sub('[=:]', ".", testname)
            if self.test_name != testname:
                continue
            if testcase.findall("failure") or testcase.findall("error"):
                print "TEST FAILED: " + rev
                return False

            if testcase.findall("skipped"):
                print "INFO: the target test was skipped"
            print "TEST PASSED: " + rev
            return True

        print "ERROR -- TEST NOT FOUND, treating as success: " + rev + " " + self.test_name
        return True
    
class TestLister:
    """reads xml files and generates a set of PiglitTest objects"""
    def __init__(self, bad_dir):
        self._tests = {}
        self._tests["piglit-test"] = {}
        # used to limit the number of tests run to the ones that are
        # under bisection
        self._retest_path = os.path.abspath(bad_dir + "/..")
        # self.test_map is keyed by test name, value is PiglitTest
        for a_file in os.listdir(bad_dir):
            if ("piglit-test" not in a_file and
                "piglit-cpu-test" not in a_file and
                "piglit-deqp" not in a_file) :
                continue
            test_path = bad_dir + "/" + a_file
            self._add_tests(test_path)

    def _add_tests(self, test_path):
        t = ET.parse(test_path)
        r = t.getroot()

        for afail in r.findall(".//failure/..") + r.findall(".//error/.."):
            piglit_test = PiglitTest(full_test_name="unknown", 
                                     status="unknown",
                                     test_tag=afail,
                                     retest_path=self._retest_path)

            project = piglit_test.project
            name = piglit_test.test_name
            if name not in self._tests[project]:
                self._tests[project][name] = piglit_test
                continue
            self._tests[project][name].AddTest(piglit_test)

    def Print(self):
        for project in self._tests.values():
            for test in project.values():
                test.Print()

    def Tests(self):
        tests = []
        for project in self._tests.values():
            tests = tests + project.values()
        return tests

    def TestsNotIn(self, other_test_list):
        out_list = []
        for (project, tests) in self._tests.items():
            for (name, test) in tests.items():
                if name not in other_test_list._tests[project]:
                    out_list.append(test)
                    continue
                other_test = other_test_list._tests[project][name]
                if other_test.arch != test.arch or other_test.hardware != test.hardware:
                    # didn't get the same primary failure.  It's likely
                    # that the test was marked as fixed for only one
                    # platform
                    out_list.append(test)
                    continue
        return out_list
