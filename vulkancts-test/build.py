#!/usr/bin/python

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

class SlowTimeout:
    def __init__(self):
        pass

    def GetDuration(self):
        return 500

class VulkanTestList(object):
    def __init__(self):
        self.pm = bs.ProjectMap()

    def tests(self, env):
        # provide a DeqpTrie with all tests
        deqp_dir = os.path.dirname(self.binary())
        os.chdir(deqp_dir)
        cmd = ["./" + os.path.basename(self.binary()),
               "--deqp-runmode=xml-caselist"]
        bs.run_batch_command(cmd, env=env)
        trie = bs.DeqpTrie()
        trie.add_xml("dEQP-VK-cases.xml")
        os.chdir(self.pm.project_build_dir())
        return trie
    
    def binary(self):
        return self.pm.build_root() + "/opt/deqp/modules/vulkan/deqp-vk"

    def blacklist(self, all_tests):
        # filter tests for the platform
        o = bs.Options()
        blacklist_file = self.pm.project_build_dir() + o.hardware[:3] + "_expectations/vk_unstable_tests.txt"
        if "glk" in o.hardware:
            blacklist_file = self.pm.project_source_dir("prerelease") + "/vulkancts-test/glk_expectations/vk_unstable_tests.txt"
        blacklist = bs.DeqpTrie()
        blacklist.add_txt(blacklist_file)
        all_tests.filter(blacklist)

class VulkanTester(object):
    def build(self):
        pass
    def clean(self):
        pass
    def test(self):
        pm = bs.ProjectMap()
        env={"VK_ICD_FILENAMES" : pm.build_root() + \
             "/usr/share/vulkan/icd.d/dev_icd.json"}
        tester = bs.DeqpTester()
        binary = pm.build_root() + "/opt/deqp/modules/vulkan/deqp-vk"
        results = tester.test(binary,
                              VulkanTestList(),
                              ["--deqp-surface-type=fbo"],
                              env=env)
        o = bs.Options()
        mv = bs.mesa_version()
        if "glk" in o.hardware and "13.0" in mv:
            print "WARNING: glk not supported by stable mesa"
            return
        config = bs.get_conf_file(o.hardware, o.arch, project=pm.current_project())
        tester.generate_results(results, bs.ConfigFilter(config, o))

bs.build(VulkanTester(),
         time_limit=SlowTimeout())

