#!/usr/bin/python

import ConfigParser
import glob
import multiprocessing
import os
import subprocess
import sys
import time
import xml.sax.saxutils as saxutils

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

# needed to preserve case in the options
class CaseConfig(ConfigParser.SafeConfigParser):
    def optionxform(self, optionstr):
        return optionstr

class CtsTestList(object):
    def __init__(self):
        self.pm = bs.ProjectMap()
        self.o = bs.Options()

    def tests(self, env):
        br = self.pm.build_root()
        whitelists = {
            "ES2-CTS-cases.xml": br + "/bin/es/cts/gl_cts/data/aosp_mustpass/gles2-master.txt",
            "ES3-CTS-cases.xml": br + "/bin/es/cts/gl_cts/data/aosp_mustpass/gles3-master.txt",
            "ES31-CTS-cases.xml": br + "/bin/es/cts/gl_cts/data/aosp_mustpass/gles31-master.txt",
            "ES32-CTS-cases.xml": br + "/bin/es/cts/gl_cts/data/aosp_mustpass/gles32-master.txt",
            }

        # provide a DeqpTrie with all tests
        binary = br + "/bin/es/cts/glcts"
        cts_dir = os.path.dirname(binary)
        os.chdir(cts_dir)
        save_override = env["MESA_GLES_VERSION_OVERRIDE"]
        env["MESA_GLES_VERSION_OVERRIDE"] = "3.2"
        cmd = [binary,
               "--deqp-runmode=xml-caselist"]
        bs.run_batch_command(cmd, env=env)
        env["MESA_GLES_VERSION_OVERRIDE"] = save_override
        all_tests = bs.DeqpTrie()
        for caselist in glob.glob("*.xml"):
            testlist = bs.DeqpTrie()
            testlist.add_xml(caselist)
            if caselist in whitelists:
                whitelist = bs.DeqpTrie()
                whitelist.add_txt(whitelists[caselist])

                # add GTF tests, which are not in the whitelists
                suite = "-".join(caselist.split("-")[:2]) + ".gtf.*"
                whitelist.add_line(suite)
                testlist.filter_whitelist(whitelist)

            # combine test list into single file
            all_tests.merge(testlist)
        os.chdir(self.pm.project_build_dir())
        return all_tests

    def blacklist(self, all_tests):
        project = self.pm.current_project()
        blacklist_dir = self.pm.project_build_dir(project) + "/"
        blacklist = bs.DeqpTrie()
        if "bxt" in self.o.hardware:
            blacklist_dir = self.pm.project_source_dir("prerelease") + "/" + project + "/"
        blacklist_file = blacklist_dir + self.o.hardware + self.o.arch + "_blacklist.txt"
        if os.path.exists(blacklist_file):
            blacklist.add_txt(blacklist_file)
            return blacklist
        blacklist_file = blacklist_dir + self.o.hardware + "_blacklist.txt"
        if os.path.exists(blacklist_file):
            blacklist.add_txt(blacklist_file)
            return blacklist
        blacklist_file = blacklist_dir + self.o.hardware[:3] + "_blacklist.txt"
        if os.path.exists(blacklist_file):
            blacklist.add_txt(blacklist_file)
        all_tests.filter(blacklist)
        mesa_version = bs.mesa_version()
        unsupported = []
        if "11.2" in mesa_version:
            unsupported = ["ES32-CTS"]
            if self._gen() < 8.0:
                unsupported.append("ES31-CTS")
            if self._gen() < 6.0:
                unsupported.append("ES30-CTS")

        if "12.0" in mesa_version:
            if self._gen() < 8.0:
                unsupported.append("ES31-CTS")

        all_tests.filter(unsupported)        

    def _gen(self):
        if "skl" in self.o.hardware or "kbl" in self.o.hardware or "bxt" in self.o.hardware:
            return 9.0
        if "bdw" in self.o.hardware or "bsw" in self.o.hardware:
            return 8.0
        if "hsw" in self.o.hardware:
            return 7.5
        if "ivb" in self.o.hardware or "byt" in self.o.hardware:
            return 7.0
        if "snb" in self.o.hardware:
            return 6.0
        if "ilk" in self.o.hardware:
            return 5.0
        assert("g965" in self.o.hardware or "g33" in self.o.hardware or "g45" in self.o.hardware)
        return 4.0

class GLESCTSTester(object):
    def __init__(self):
        self.o = bs.Options()
        self.pm = bs.ProjectMap()

        self.env = {"MESA_GLES_VERSION_OVERRIDE" : ""}
        if self._gles_32():
            self.env["MESA_GLES_VERSION_OVERRIDE"] = "3.2"
        elif self._gles_31():
            self.env["MESA_GLES_VERSION_OVERRIDE"] = "3.1"

    def _gles_32(self):
        return ("skl" in self.o.hardware or
                "kbl" in self.o.hardware or
                "bxt" in self.o.hardware)
        
    def _gles_31(self):
        return ("hsw" in self.o.hardware or
                "bdw" in self.o.hardware or
                "bsw" in self.o.hardware or
                "byt" in self.o.hardware or
                "ivb" in self.o.hardware)
    
    def test(self):
        t = bs.DeqpTester()
        results = t.test(self.pm.build_root() + "/bin/es/cts/glcts",
                         CtsTestList(),
                         [],
                         self.env)

        o = bs.Options()
        config = bs.get_conf_file(self.o.hardware, self.o.arch, project=self.pm.current_project())
        t.generate_results(results, bs.ConfigFilter(config, o))
        
    def build(self):
        pass
    def clean(self):
        pass

class SlowTimeout:
    def __init__(self):
        self.hardware = bs.Options().hardware

    def GetDuration(self):
        return 500

bs.build(GLESCTSTester(), time_limit=SlowTimeout())
