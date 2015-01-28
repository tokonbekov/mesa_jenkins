import re
import os
import time
import xml.etree.ElementTree as ET

from . import RevisionSpecification
from . import Options
from . import ProjectMap
from . import rmtree
from . import Jenkins
from . import DependencyGraph
from . import ProjectInvoke
from . import BuildFailure
#from . import 


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
            repo_project = "piglit-build"
        rev = repo_project + "=" + self.commits[current_build].hexsha
        print "Range: " + self.commits[0].hexsha + " - " + self.commits[-1].hexsha
        print "Building revision: " + rev

        o = Options(args=["ignore"])
        o.type = "developer"
        o.config = "debug"
        o.arch = self.arch
        o.hardware = self.hardware
        o.action = ["build", "test"]

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
            jen.build_all(depGraph, "bisect")
            print "Starting: " + bi.to_short_string()
            test_name_good_chars = re.sub('[_ !:]', ".", self.test_name)
            jen.build(bi, branch="mesa_master", extra_arg="--piglit_test=" + test_name_good_chars)
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
            if self.test_name not in testname:
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
