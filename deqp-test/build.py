#!/usr/bin/python

import sys, os
import bz2
import xml.etree.ElementTree  as ET

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

class DeqpTrie:
    def __init__(self):
        self._trie = {}
        
    def add_txt(self, txt_file):
        fh = None
        if (txt_file[-4:] == ".bz2"):
            fh = bz2.BZ2File(txt_file)
        else:
            fh = open(txt_file)

        for line in fh.readlines():
            line = line.strip()
            self._add_split_line(line.split("."))

    def _add_split_line(self, line):
        if not line:
            return
        group = line[0]
        if not self._trie.has_key(group):
            self._trie[group] = DeqpTrie()
        self._trie[group]._add_split_line(line[1:])
            
    def add_xml(self, xml_file):
        current_trie = None
        if "dEQP-GLES2-cases" in xml_file:
            current_trie = DeqpTrie()
            self._trie["dEQP-GLES2"] = current_trie
        elif "dEQP-GLES3-cases" in xml_file:
            current_trie = DeqpTrie()
            self._trie["dEQP-GLES3"] = current_trie
        else:
            return
        root = ET.parse(xml_file).getroot()
        for tag in root:
            current_trie._add_tag(tag)

    def _add_tag(self, tag):
        name = tag.attrib["Name"]
        if not self._trie.has_key(name):
            self._trie[name] = DeqpTrie()

        for child in tag:
            self._trie[name]._add_tag(child)

    def filter(self, blacklist):
        for group in blacklist._trie.keys():
            if group not in self._trie:
                print "ERROR: blacklist of " + group + " not in tests"
                continue
            self._trie[group].filter(blacklist._trie[group])
            if len(self._trie[group]._trie) == 0:
                del(self._trie[group])

    def write_caselist(self, outfh, prefix=""):
        for group, trie in self._trie.items():
            if len(trie._trie) == 0:
                outfh.write(prefix + "." + group + "\n")
                continue
            # else
            if prefix:
                group = prefix + "." + group
            trie.write_caselist(outfh, group)
            
class DeqpBuilder:
    def __init__(self):
        o = bs.Options()
        pm = bs.ProjectMap()
        self.build_root = pm.build_root()
        libdir = "x86_64-linux-gnu"
        if o.arch == "m32":
            libdir = "i386-linux-gnu"
        self.env = { "LD_LIBRARY_PATH" : self.build_root + "/lib:" + \
                self.build_root + "/lib/" + libdir + ":" + self.build_root + "/lib/dri",
                "LIBGL_DRIVERS_PATH" : self.build_root + "/lib/dri",
                "GBM_DRIVERS_PATH" : self.build_root + "/lib/dri",
                # fixes dxt subimage tests that fail due to a
                # combination of unreasonable tolerances and possibly
                # bugs in debian's s2tc library.  Recommended by nroberts
                "S2TC_DITHER_MODE" : "NONE"
        }

    def build(self):
        pass

    def clean(self):
        pass

    def test(self):
        o = bs.Options()
        pm = bs.ProjectMap()
        src_dir = pm.project_source_dir(pm.current_project())
        savedir = os.getcwd()

        deqp_options = ["./deqp-gles2",
                        "--deqp-surface-type=fbo",
                        "--deqp-log-images=disable",
                        "--deqp-surface-width=100",
                        "--deqp-surface-height=100"]


        expectations_dir = None
        # identify platform
        if "byt" in o.hardware:
            expectations_dir = src_dir + "/chromiumos-autotest/graphics_dEQP/expectations/baytrail"
        elif "bdw" in o.hardware:
            expectations_dir = src_dir + "/chromiumos-autotest/graphics_dEQP/expectations/broadwell"
        elif "hsw" in o.hardware:
            expectations_dir = src_dir + "/chromiumos-autotest/graphics_dEQP/expectations/haswell"
        elif "ivb" in o.hardware:
            expectations_dir = src_dir + "/chromiumos-autotest/graphics_dEQP/expectations/ivybridge"
        elif "snb" in o.hardware:
            expectations_dir = src_dir + "/chromiumos-autotest/graphics_dEQP/expectations/sandybridge"

        for module in ["gles2", "gles3"]:
            skip = DeqpTrie()
            # for each skip list, parse into skip trie
            for askipfile in os.listdir(expectations_dir):
                if module not in askipfile.lower():
                    continue
                skip.add_txt(expectations_dir + "/" + askipfile)

            # create test trie
            os.chdir(self.build_root + "/opt/deqp/modules/" + module)
            # generate list of tests
            bs.run_batch_command(["./deqp-" + module] + deqp_options + ["--deqp-runmode=xml-caselist"],
                                 env=self.env)
            outfile = "dEQP-" + module.upper() + "-cases.xml"
            assert(os.path.exists(outfile))
            testlist = DeqpTrie()
            testlist.add_xml(outfile)

            # filter skip trie from testlist trie
            testlist.filter(skip)

            # generate testlist file
            caselist = open(module + "-cases.txt", "w")
            testlist.write_caselist(caselist)

        # invoke piglit
        self.env["PIGLIT_DEQP_GLES2_BIN"] = self.build_root + "/opt/deqp/modules/gles2/deqp-gles2"
        self.env["PIGLIT_DEQP_GLES2_EXTRA_ARGS"] =  ("--deqp-surface-type=fbo "
                                                     "--deqp-log-images=disable "
                                                     '--deqp-surface-width=100 '
                                                     '--deqp-surface-height=100 '
                                                     "--deqp-caselist-file=" +
                                                     self.build_root + "/opt/deqp/modules/gles2/gles2-cases.txt")
        self.env["PIGLIT_DEQP_GLES3_EXE"] = self.build_root + "/opt/deqp/modules/gles3/deqp-gles3"
        self.env["PIGLIT_DEQP_GLES3_EXTRA_ARGS"] = ("--deqp-surface-type=fbo "
                                                    "--deqp-log-images=disable "
                                                    '--deqp-surface-width=100 '
                                                    '--deqp-surface-height=100 '
                                                    "--deqp-caselist-file=" +
                                                    self.build_root + "/opt/deqp/modules/gles3/gles3-cases.txt")
        out_dir = self.build_root + "/test/" + o.hardware
        cmd = [self.build_root + "/bin/piglit",
               "run",
               "-p", "gbm",
               "-b", "junit",
               "--junit_suffix", "." + o.hardware + o.arch,
               "deqp_gles2", "deqp_gles3", out_dir ]
            
        bs.run_batch_command(cmd, env=self.env,
                             expected_return_code=None,
                             streamedOutput=True)
        os.chdir(savedir)
        

bs.build(DeqpBuilder())
        
