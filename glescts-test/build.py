#!/usr/bin/python

#import ConfigParser
import multiprocessing
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

# needed to preserve case in the options
# class CaseConfig(ConfigParser.SafeConfigParser):
#     def optionxform(self, optionstr):
#         return optionstr

class GLCTSList(object):
    def __init__(self):
        self.pm = bs.ProjectMap()
        self.o = bs.Options()

    def supports_gles_31(self):
        if ("g33" in self.o.hardware or
            "g45" in self.o.hardware or
            "g965" in self.o.hardware or
            "ilk" in self.o.hardware or
            "snb" in self.o.hardware):
            return False
        return True

    def supports_gles_32(self):
        if not self.supports_gles_31():
            return False

        if ("hsw" in self.o.hardware or
            "bdw" in self.o.hardware or
            "bsw" in self.o.hardware or
            "byt" in self.o.hardware or
            "ivb" in self.o.hardware):
            return False

        # all newer platforms support 3.2
        return True

    def tests(self, env=None):
        br = self.pm.build_root()
        libdir = "x86_64-linux-gnu"
        if self.o.arch == "m32":
            libdir = "i386-linux-gnu"
        env = {"MESA_GLES_VERSION_OVERRIDE" : "3.2",
               "LD_LIBRARY_PATH" : br + "/lib",
               "LIBGL_DRIVERS_PATH" : br + "/lib/dri"}
        self.o.update_env(env)

        savedir = os.getcwd()
        os.chdir(self.pm.build_root() + "/bin/es/modules")
        bs.run_batch_command(["./glcts", "--deqp-runmode=xml-caselist"],
                             env=env)
        all_tests = bs.DeqpTrie()

        all_tests.add_xml("dEQP-EGL-cases.xml")
        all_tests.add_xml("dEQP-GLES2-cases.xml")
        all_tests.add_xml("KHR-GLES2-cases.xml")
        all_tests.add_xml("KHR-GLES3-cases.xml")
        all_tests.add_xml("dEQP-GLES3-cases.xml")

        if self.supports_gles_31():
            all_tests.add_xml("dEQP-GLES31-cases.xml")
            all_tests.add_xml("KHR-GLES31-cases.xml")

        if self.supports_gles_32():
            all_tests.add_xml("KHR-GLES32-cases.xml")
            all_tests.add_xml("KHR-GLESEXT-cases.xml")

        os.chdir(savedir)
        return all_tests

    def blacklist(self, all_tests):
        blacklist_txt = self.pm.project_build_dir() + "/" + self.o.hardware[:3] + "_blacklist.txt"
        if not os.path.exists(blacklist_txt):
            return all_tests
        blacklist = bs.DeqpTrie()
        blacklist.add_txt(blacklist_txt)
        all_tests.filter(blacklist)
        return all_tests

class GLCTSTester(object):
    def __init__(self):
        self.o = bs.Options()
        self.pm = bs.ProjectMap()

    def test(self):
        mv = bs.mesa_version()
        if "17.2" in mv or "17.1" in mv:
            return
        t = bs.DeqpTester()
        results = t.test(self.pm.build_root() + "/bin/es/modules/glcts",
                         GLCTSList(),
                         env = {"MESA_GLES_VERSION_OVERRIDE" : "3.2"}) 
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
        return 120

bs.build(GLCTSTester(), time_limit=SlowTimeout())
