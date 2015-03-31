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
#from . import 

def get_conf_file(hardware, arch, nir):
    # strip the gtX strings off of the hardware, because there are
    # no examples where a sku has a different config
    if "gt" in hardware:
        hardware = hardware[:3]
    conf_dir = ProjectMap().source_root() + "/piglit-test/"
    conf_file = conf_dir + "/" + hardware + arch + ".conf"
    if not os.path.exists(conf_file):
        conf_file = conf_dir + "/" + hardware + ".conf"
    if nir:
        # if a nir-specific conf file exists, use it instead
        # of the hw/arch conf file.
        nir_conf = conf_file[:-5] + "nir.conf"
        if os.path.exists(nir_conf):
            conf_file = nir_conf

    assert (os.path.exists(conf_file))
    return conf_file

class Bisector:
    def __init__(self, project, test_name, arch, hardware,
                 commits):
        self.project = project
        # remove inadvertent whitespace, which is easy to add when
        # triggering builds on jenkins
        self.test_name = test_name.strip()
        self.arch = arch
        self.hardware = hardware
        self.commits = commits
        self.last_failure = None

    def Bisect(self):
        if not self.commits:
            return
        current_build = len(self.commits) / 2
        repo_project = self.project
        if repo_project == "piglit-test":
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
        rmtree(result_path + "/test")

        global jen
        jen = Jenkins(result_path=result_path,
                         revspec=revspec)

        depGraph = DependencyGraph("piglit-test", o)
        # remove test build from graph, because we always want to build
        # it.
        bi = ProjectInvoke(project="piglit-test", 
                              options=o)
        bi.set_info("status", "bisect-rebuild")

        depGraph.build_complete(bi)
        try:
            jen.build_all(depGraph, "bisect", extra_arg=None, print_summary=False)
            print "Starting: " + bi.to_short_string()
            test_name_good_chars = re.sub('[_ !:=]', ".", self.test_name)
            jen.build(bi, branch="mesa_master", extra_arg="--piglit_test=" + test_name_good_chars + ".anyhardware")
            jen.wait_for_build()
        except BuildFailure:
            print "BUILD FAILED - exception: " + rev
            if current_build + 1 == len(self.commits):
                print "FIRST DETECTED FAILURE: " + rev
                return rev
            self.last_failure = rev
            self.commits = self.commits[current_build+1:]
            return self.Bisect()

        test_result = "/".join([result_path, "test", "piglit-test_" + 
                                o.hardware + "_" + o.arch + ".xml"])
        iteration = 0
        while not os.path.exists(test_result):
            if iteration < 40:
                time.sleep(1)
                iteration = iteration + 1
                continue
            print "BUILD FAILED - no test results: " + rev + " : " + test_result
            self.last_failure = rev
            if current_build + 1 == len(self.commits):
                print "FIRST DETECTED FAILURE: " + rev
                return rev
            self.commits = self.commits[current_build + 1:]
            return self.Bisect()

        result = ET.parse(test_result)
        for testcase in result.findall("./testsuite/testcase"):
            testname = testcase.attrib["classname"] + "." + testcase.attrib["name"]
            #strip off the arch/platform and drop the special characters
            testname = ".".join(testname.split(".")[:-1])
            testname = re.sub('[=:]', ".", testname)
            if self.test_name != testname:
                continue
            if testcase.findall("skipped"):
                print "ERROR: the target test was skipped"
                assert(False)
            if testcase.findall("failure") or testcase.findall("error"):
                print "TEST FAILED: " + rev
                self.last_failure = rev
                if current_build + 1 == len(self.commits):
                    print "FIRST DETECTED FAILURE: " + rev
                    return rev
                self.commits = self.commits[current_build + 1:]
                return self.Bisect()

            print "TEST PASSED: " + rev
            if current_build == 0:
                print "LAST DETECTED SUCCESS: " + rev
                return self.last_failure
            self.commits = self.commits[:current_build]
            return self.Bisect()

        print "ERROR -- TEST NOT FOUND: " + self.test_name
        if current_build == 0:
            print "LAST DETECTED SUCCESS: " + rev
            return self.last_failure
        self.commits = self.commits[:current_build]
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
    preferred_hardware = ["hswgt3e", "hswgt2", "hswgt1", "ivbgt2",
                          "ivbgt1"] # ...

    def __init__(self, full_test_name, status, test_tag=None):
        """full_test_name includes arch/platform.  status must be one
        of "pass", "fail", "crash" """

        if test_tag is not None:
            full_test_name = test_tag.attrib["name"]
            full_test_name = test_tag.attrib["classname"] + "." + full_test_name
            full_test_name = full_test_name.replace("=", ".")
            full_test_name = full_test_name.replace(":", ".")
            failnode = test_tag.find("./failure")
            if failnode is not None:
                status = failnode.attrib["type"]
            else:
                status = "crash"
        
        arch_hardware = full_test_name.split(".")[-1]
        arch = arch_hardware[-3:]
        hardware = arch_hardware[:-3]
        self.nir = False
        if "nir_" in hardware:
            hardware = hardware[4:]
            self.nir = True
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

    def Bisect(self, project, commits):
        print "Bisecting for " + self.test_name
        b = Bisector(project, self.test_name, self.arch, self.hardware, commits)
        self.bisected_revision = b.Bisect()
        if not self.bisected_revision:
            print "No bisection found for " + self.test_name
            return
        self.bisected_revision = self.bisected_revision.replace("=", " ")

    def GetConf(self):
        return get_conf_file(self.hardware, self.arch, self.nir)

        
    def UpdateConf(self):
        if not self.bisected_revision:
            return
        full_list = [(self.arch, self.hardware)] + self.other_arches
        for _, hardware in full_list:
            if "gt" in hardware:
                hardware = hardware[:3]
            conf_file = self.GetConf()
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
        conf_file = self.GetConf()
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

    def _add_tests(self, test_path):
        t = ET.parse(test_path)
        r = t.getroot()

        for afail in r.findall(".//failure/..") + r.findall(".//error/.."):
            piglit_test = PiglitTest(full_test_name="unknown", 
                                     status="unknown",
                                     test_tag=afail)
            
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
