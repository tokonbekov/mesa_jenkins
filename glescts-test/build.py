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

class GLESCTSList(object):
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
        env = {"MESA_GLES_VERSION_OVERRIDE" : "3.2",
               "LD_LIBRARY_PATH" : bs.get_libdir(),
               "MESA_GL_VERSION_OVERRIDE" : "4.6",
               "MESA_GLSL_VERSION_OVERRIDE" : "460",
               "LIBGL_DRIVERS_PATH" : bs.get_libgl_drivers()}
        self.o.update_env(env)

        savedir = os.getcwd()
        os.chdir(self.pm.build_root() + "/bin/es/modules")
        bs.run_batch_command(["./glcts", "--deqp-runmode=xml-caselist"],
                             env=env)

        must_pass_root = br + "/bin/es/modules/gl_cts/data/mustpass/"
        must_pass_lookup = { "KHR-GLES2-cases.xml" : "gles/khronos_mustpass/3.2.4.x/gles2-khr-master.txt",
                             "KHR-GLES3-cases.xml" : "gles/khronos_mustpass/3.2.4.x/gles3-khr-master.txt",
                             "KHR-GLES31-cases.xml" : "gles/khronos_mustpass/3.2.4.x/gles31-khr-master.txt",
                             "KHR-GLES32-cases.xml" : "gles/khronos_mustpass/3.2.4.x/gles32-khr-master.txt",
                             "KHR-GLESEXT-cases.xml" : None }

        suites = ["KHR-GLES2-cases.xml", "KHR-GLES3-cases.xml"]

        if self.supports_gles_31():
            suites.append("KHR-GLES31-cases.xml")

        if self.supports_gles_32():
            suites.append("KHR-GLES32-cases.xml")
            suites.append("KHR-GLESEXT-cases.xml")

        all_tests = bs.DeqpTrie()
        for a_list in suites:
            tmp_trie = bs.DeqpTrie()
            tmp_trie.add_xml(a_list)
            if must_pass_lookup[a_list]:
                tmp_whitelist = bs.DeqpTrie()
                tmp_whitelist.add_txt(must_pass_root + must_pass_lookup[a_list])
                tmp_trie.filter_whitelist(tmp_whitelist)
            all_tests.merge(tmp_trie)

        os.chdir(savedir)
        return all_tests

    def blacklist(self, all_tests):
        blacklist_txt = self.pm.project_build_dir() + "/" + self.o.hardware + "_blacklist.txt"
        if not os.path.exists(blacklist_txt):
            blacklist_txt = self.pm.project_build_dir() + "/" + self.o.hardware[:3] + "_blacklist.txt"
        if not os.path.exists(blacklist_txt):
            return all_tests
        blacklist = bs.DeqpTrie()
        blacklist.add_txt(blacklist_txt)
        all_tests.filter(blacklist)
        return all_tests

class GLESCTSTester(object):
    def __init__(self):
        self.o = bs.Options()
        self.pm = bs.ProjectMap()

    def test(self):
        mv = bs.mesa_version()
        if "17.2" in mv or "17.1" in mv:
            return
        t = bs.DeqpTester()
        results = t.test(self.pm.build_root() + "/bin/es/modules/glcts",
                         GLESCTSList(),
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

bs.build(GLESCTSTester(), time_limit=SlowTimeout())
