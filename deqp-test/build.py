#!/usr/bin/python

import os
import sys
import subprocess

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs


class SlowTimeout:
    def __init__(self):
        self.hardware = bs.Options().hardware

    def GetDuration(self):
        return 500

class DeqpLister(object):
    def __init__(self, binary, cts_tests):
        self.binary = binary
        self.o = bs.Options()
        self.pm = bs.ProjectMap()
        self.blacklist_txt = None
        self.cts_blacklist = cts_tests

    def tests(self, env):
        # don't execute tests that are part of the other suite
        whitelist_txt = None
        cases_xml = None
        bd = self.pm.project_build_dir()
        if "gles2" in self.binary:
            whitelist_txt = self.pm.project_source_dir("deqp") + "/android/cts/master/gles2-master.txt"
            cases_xml = "dEQP-GLES2-cases.xml"
            self.blacklist_txt = bd + self.o.hardware[:3] + "_expectations/gles2_unstable_tests.txt"
        if "gles3" in self.binary:
            whitelist_txt = self.pm.project_source_dir("deqp") + "/android/cts/master/gles3-master.txt"
            cases_xml = "dEQP-GLES3-cases.xml"
            self.blacklist_txt = bd + self.o.hardware[:3] + "_expectations/gles3_unstable_tests.txt"
        if "gles31" in self.binary:
            whitelist_txt = self.pm.project_source_dir("deqp") + "/android/cts/master/gles31-master.txt"
            cases_xml = "dEQP-GLES31-cases.xml"
            self.blacklist_txt = bd + self.o.hardware[:3] + "_expectations/gles31_unstable_tests.txt"
        deqp_dir = os.path.dirname(self.binary)
        os.chdir(deqp_dir)
        cmd = [self.binary,
               "--deqp-runmode=xml-caselist"]
        bs.run_batch_command(cmd, env=env)
        all_tests = bs.DeqpTrie()
        all_tests.add_xml(cases_xml)
        whitelist = bs.DeqpTrie()
        whitelist.add_txt(whitelist_txt)
        all_tests.filter_whitelist(whitelist)
        os.chdir(self.pm.project_build_dir())
        all_tests.filter(self.cts_blacklist)
        return all_tests

    def blacklist(self, all_tests):
        blacklist = bs.DeqpTrie()
        blacklist.add_txt(self.blacklist_txt)
        mesa_version = bs.mesa_version()
        unsupported = []
        if "daily" != self.o.type and not self.o.retest_path:
            # these tests triple the run-time
            unsupported.append("dEQP-GLES31.functional.copy_image")
        if "11.2" in mesa_version:
            if bs.generation(self.o) < 8.0:
                unsupported.append("dEQP-GLES31")
            if bs.generation(self.o) < 6.0:
                unsupported.append("dEQP-GLES3")

        if "12.0" in mesa_version:
            if bs.generation(self.o) < 8.0:
                unsupported.append("dEQP-GLES31")
        if bs.generation(self.o) < 7.0:
            unsupported.append("dEQP-GLES31")
        all_tests.filter(unsupported)
        
class DeqpBuilder(object):
    def __init__(self):
        self.pm = bs.ProjectMap()
        self.o = bs.Options()
        self.env = {}
    def build(self):
        pass
    def clean(self):
        pass
    def test(self):
        cts_blacklist = bs.CtsTestList().tests()
        for suite in ["ES32", "ES31", "ES3", "ES2"]:
            if suite + "-CTS" in cts_blacklist._trie:
                cts_blacklist._trie["dEQP-GL" + suite] = cts_blacklist._trie[suite + "-CTS"]
        if "hsw" in self.o.hardware or "byt" in self.o.hardware or "ivb" in self.o.hardware:
            self.env["MESA_GLES_VERSION_OVERRIDE"] = "3.1"
        t = bs.DeqpTester()
        all_results = bs.DeqpTrie()
        modules = ["gles2", "gles3", "gles31"]
        if "skl" in self.o.hardware or "bdw" in self.o.hardware or "bsw" in self.o.hardware or "hsw" in self.o.hardware or "byt" in self.o.hardware or "ivb" in self.o.hardware:
            modules += ["gles31"]

        for module in modules:
            binary = self.pm.build_root() + "/opt/deqp/modules/" + module + "/deqp-" + module
            results = t.test(binary,
                             DeqpLister(binary, cts_blacklist),
                             [],
                             self.env)
            all_results.merge(results)

        config = bs.get_conf_file(self.o.hardware, self.o.arch, project=self.pm.current_project())
        t.generate_results(all_results, bs.ConfigFilter(config, self.o))
        
bs.build(DeqpBuilder(), time_limit=SlowTimeout())
        
