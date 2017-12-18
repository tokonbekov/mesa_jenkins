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

    def tests(self, env=None):
        br = self.pm.build_root()
        env = {"MESA_GLES_VERSION_OVERRIDE" : "3.2",
               "LD_LIBRARY_PATH" : bs.get_libdir(),
               "LIBGL_DRIVERS_PATH" : bs.get_libgl_drivers(),
               "MESA_GL_VERSION_OVERRIDE" : "4.6",
               "MESA_GLSL_VERSION_OVERRIDE" : "460"}
        self.o.update_env(env)

        savedir = os.getcwd()
        os.chdir(self.pm.build_root() + "/bin/gl/modules")
        bs.run_batch_command(["./glcts", "--deqp-runmode=xml-caselist"],
                             env=env)
        all_tests = bs.DeqpTrie()
        # Note: ilk, g45, etc are all < GL30 and not supported in glcts
        if self.o.hardware in ['snb', 'ivb', 'byt']:
            all_tests.add_xml("KHR-GL33-cases.xml")
        else:
            all_tests.add_xml("KHR-GL46-cases.xml")
        os.chdir(savedir)
        return all_tests

    def blacklist(self, all_tests):
        blacklist_txt = self.pm.project_build_dir() + "/" + self.o.hardware[:3] + "_blacklist.txt"
        if not os.path.exists(blacklist_txt):
            return all_tests
        blacklist = bs.DeqpTrie()
        blacklist.add_txt(blacklist_txt)
        all_tests.filter(blacklist)
        if "17.3" in bs.mesa_version():
            blacklist = bs.DeqpTrie()
            blacklist.add_txt(self.pm.project_build_dir() + "/17_3_blacklist.txt")
            all_tests.filter(blacklist)
        if self.o.type != "daily" and not self.o.retest_path:
            blacklist = bs.DeqpTrie()
            blacklist.add_txt(self.pm.project_build_dir() + "/non-daily_blacklist.txt")
            all_tests.filter(blacklist)

        return all_tests

class GLCTSTester(object):
    def __init__(self):
        self.o = bs.Options()
        self.pm = bs.ProjectMap()

    def test(self):
        mv = bs.mesa_version()
        if "17.2" in mv or "17.1" in mv:
            print("NOTICE: GLCTS will NOT be run since the system has Mesa version <17.3")
            return
        t = bs.DeqpTester()
        results = t.test(self.pm.build_root() + "/bin/gl/modules/glcts",
                         GLCTSList(),
                         env = {"MESA_GL_VERSION_OVERRIDE" : "4.6",
                                "MESA_GLSL_VERSION_OVERRIDE" : "460"})

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
