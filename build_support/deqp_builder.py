#!/usr/bin/python
import bz2
import os
import xml.etree.ElementTree as ET

from . import *

class DeqpTrie:
    def __init__(self):
        self._trie = {}
        self._result = {}
        self._content = {}
        self._duration = {}
        self._stdout = {}
        self._stderr = {}

    def empty(self):
        return not self._trie

    def results_count(self, running_count = 0):
        for _,v in iter(self._trie.items()):
            running_count = v.results_count(running_count)
        running_count += len(self._result)
        return running_count
    
    def add_txt(self, txt_file):
        fh = None
        if (txt_file[-4:] == ".bz2"):
            fh = bz2.BZ2File(txt_file)
        else:
            fh = open(txt_file)

        for line in fh.readlines():
            line = line.strip()
            self.add_line(line)

    def add_line(self, line):
        self._add_split_line(line.split("."))
            
    def _add_split_line(self, line):
        if not line:
            return
        group = line[0]
        if line == "performance":
            return
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
        elif "dEQP-GLES31-cases" in xml_file:
            current_trie = DeqpTrie()
            self._trie["dEQP-GLES31"] = current_trie
        elif "dEQP-VK-cases" in xml_file:
            current_trie = DeqpTrie()
            self._trie["dEQP-VK"] = current_trie
        elif "dEQP-EGL-cases" in xml_file:
            current_trie = DeqpTrie()
            self._trie["dEQP-EGL"] = current_trie
        elif "CTS-Configs-cases" in xml_file:
            current_trie = DeqpTrie()
            self._trie["CTS-Configs"] = current_trie
        elif "ES2-CTS-cases" in xml_file:
            current_trie = DeqpTrie()
            self._trie["ES2-CTS"] = current_trie
        elif "ES3-CTS-cases" in xml_file:
            current_trie = DeqpTrie()
            self._trie["ES3-CTS"] = current_trie
        elif "ES31-CTS-cases" in xml_file:
            current_trie = DeqpTrie()
            self._trie["ES31-CTS"] = current_trie
        elif "ES32-CTS-cases" in xml_file:
            current_trie = DeqpTrie()
            self._trie["ES32-CTS"] = current_trie
        elif "ESEXT-CTS" in xml_file:
            current_trie = DeqpTrie()
            self._trie["ESEXT-CTS"] = current_trie
        else:
            return
        root = ET.parse(xml_file).getroot()
        for tag in root:
            current_trie._add_tag(tag)

    def _add_tag(self, tag):
        name = tag.attrib["Name"]
        if name == "performance":
            return
        if not self._trie.has_key(name):
            self._trie[name] = DeqpTrie()

        for child in tag:
            self._trie[name]._add_tag(child)

    def filter(self, blacklist):
        if not blacklist._trie and self._trie:
            # caller is filtering out a group of tests with a common
            # prefix.
            self._trie = {}
        for group in blacklist._trie.keys():
            if group not in self._trie:
                continue
            self._trie[group].filter(blacklist._trie[group])
            if len(self._trie[group]._trie) == 0:
                del(self._trie[group])

    def filter_whitelist(self, whitelist, prefix=""):
        for group in self._trie.keys():
            if group not in whitelist._trie:
                # print "DEBUG: filtering " + prefix + group + " not in whitelist"
                del (self._trie[group])
                continue
            self._trie[group].filter_whitelist(whitelist._trie[group], prefix=prefix + group + ".")

    def write_caselist(self, outfh, prefix="", shard=0, shard_count=0, current_shard=1):
        items = self._trie.items()
        # ensure stable order, so sharding will work correctly
        items.sort()
        for group, trie in items:
            if len(trie._trie) == 0:
                if shard == 0 or current_shard == shard:
                    outfh.write(prefix + "." + group + "\n")
                if shard:
                    current_shard += 1
                if current_shard > shard_count:
                    current_shard = 1
                continue
            # else
            if prefix:
                group = prefix + "." + group
            current_shard = trie.write_caselist(outfh, group, shard, shard_count, current_shard)
        return current_shard

    def merge(self, other):
        for (k, v) in iter(other._trie.items()):
            if k in self._trie:
                self._trie[k].merge(v)
            else:
                self._trie[k] = v

    def add_qpa_blob(self, split_test_name, blob, pid):
        if len(split_test_name) == 1:
            test = split_test_name[0] 
            self._trie[test] = DeqpTrie()
            self._content[test] = blob
            self._duration[test] = 0.0
            self._stdout[test] = ""
            self._stderr[test] = "pid: {}\n".format(str(pid))
            try:
                t = ET.fromstringlist(blob)
                stat_tag = t.find("./Result")
                if stat_tag is None:
                    self._result[test] = "crash"
                else:
                    self._result[test] = stat_tag.attrib["StatusCode"]
                if self._result[test] == "QualityWarning":
                    self._result[test] = "Pass"
                elif self._result[test] == "Fail":
                    out_txt = ""
                    for a_text in t.findall("./Text"):
                        out_txt += a_text.text + "\n"
                    self._stdout[test] = out_txt
                # get the test duration value
                for number in t.findall("./Number"):
                    if number.attrib["Name"] != "TestDuration":
                        continue
                    duration = float(number.text)
                    if number.attrib["Unit"] == "us":
                        duration /= 1000000.0
                    elif number.attrib["Unit"] == "ms":
                        duration /= 1000.0
                    self._duration[test] = duration
                
            except:
                self._result[test] = "crash"
            return
        group = split_test_name[0]
        if not self._trie.has_key(group):
            self._trie[group] = DeqpTrie()
        self._trie[group].add_qpa_blob(split_test_name[1:], blob, pid)

    def write_junit(self, of, config, missing_commits):
        of.write("<testsuites>\n")
        for group, t in iter(self._trie.items()):
            of.write(""" <testsuite name="{}" tests="{}">\n""".format(group, str(t.results_count())))
            self._trie[group]._write_junit_tag(of, group, config, missing_commits)
            of.write(" </testsuite>\n")
        of.write("</testsuites>")
        
    def _write_junit_tag(self, of, prefix, config, missing_commits):
        for test_name in self._result:
            status = self._result[test_name].lower()
            if status == "notsupported":
                status = "skip"
            if status not in ["pass", "crash", "skip", "fail"]:
                print "WARN: invalid status: " + test_name + " : " + status
                status = "fail"
            config.write_junit(of, prefix, test_name,
                               status,
                               self._duration[test_name],
                               self._stdout[test_name],
                               self._stderr[test_name],
                               missing_commits)
        for group in self._trie:
            self._trie[group]._write_junit_tag(of, prefix + "." + group, config, missing_commits)

    def write_nunit(self, of):
        of.write("<testsuites>\n")
        for group, t in iter(self._trie.items()):
            of.write(""" <testsuite name="{}" tests="{}">\n""".format(group, str(t.results_count())))
            self._trie[group]._write_nunit_tag(of, group)
            of.write(" </testsuite>\n")
        of.write("</testsuites>")

    def _write_nunit_tag(self, of, prefix):
        for test_name in self._result:
            status = self._result[test_name].lower()
            if status == "pass":
                of.write("""\
  <testcase classname="{}" name="{}" status="pass" time="{}"/>
""".format(prefix, test_name, self._duration[test_name]))
            elif status == "notsupported":
                status = "skip"
                of.write("""\
  <testcase classname="{}" name="{}" status="skip" time="{}">
   <skipped type="skip"/>
  </testcase>
""".format(prefix, test_name, self._duration[test_name]))
            else:
                status = "fail"
                of.write("""\
  <testcase classname="{}" name="{}" status="fail" time="{}">
   <failure type="fail"/>
   <system-out>{}</system-out>
  </testcase>
""".format(prefix, test_name, self._duration[test_name], self._stdout[test_name]))
                
        for group in self._trie:
            self._trie[group]._write_nunit_tag(of, prefix + "." + group)

class DeqpBuilder:
    def __init__(self, modules, excludes=None, env=None):
        # eg: ["gles2", "gles3"]
        self._modules = modules

        self.excludes = excludes
        if not excludes:
            self.excludes = []

        o = Options()
        pm = ProjectMap()
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
                     "S2TC_DITHER_MODE" : "NONE",
                     # forces deqp to run headless
                     "PIGLIT_NO_TIMEOUT" : "1",
                     "VK_ICD_FILENAMES" : self.build_root + "/usr/share/vulkan/icd.d/dev_icd.json"
        }
        if env:
            for (k,v) in env.items():
                self.env[k] = v
        o.update_env(self.env)

    def build(self):
        pass

    def clean(self):
        pass

    def test(self):
        o = Options()
        pm = ProjectMap()
        savedir = os.getcwd()
        
        include_tests = []
        if o.retest_path:
            testlist = TestLister(o.retest_path + "/test/")
            include_tests = testlist.RetestIncludes(pm.current_project())
            if not include_tests:
                # we were supposed to retest failures, but there were none
                return

        expectations_dir = None
        # identify platform
        if "byt" in o.hardware:
            expectations_dir = pm.project_build_dir(pm.current_project()) + "/byt_expectations"
        elif "bdw" in o.hardware:
            expectations_dir = pm.project_build_dir(pm.current_project()) + "/bdw_expectations"
        elif "hsw" in o.hardware:
            expectations_dir = pm.project_build_dir(pm.current_project()) + "/hsw_expectations"
        elif "ivb" in o.hardware:
            expectations_dir = pm.project_build_dir(pm.current_project()) + "/ivb_expectations"
        elif "snb" in o.hardware:
            expectations_dir = pm.project_build_dir(pm.current_project()) + "/snb_expectations"
        elif "bsw" in o.hardware:
            expectations_dir = pm.project_build_dir(pm.current_project()) + "/bsw_expectations"
        elif "skl" in o.hardware:
            expectations_dir = pm.project_build_dir(pm.current_project()) + "/skl_expectations"
        elif "bxt" in o.hardware:
            expectations_dir = pm.project_build_dir(pm.current_project()) + "/bxt_expectations"
        elif "kbl" in o.hardware:
            expectations_dir = pm.project_build_dir(pm.current_project()) + "/kbl_expectations"

        conf_file = get_conf_file(o.hardware, o.arch, pm.current_project())

        version = mesa_version()
        if "11.0" in version or "11.1" in version or "11.2" in version:
            if "gles31" in self._modules:
                self._modules.remove("gles31")
        for module in self._modules:
            skip = DeqpTrie()
            # for each skip list, parse into skip trie
            if expectations_dir and os.path.exists(expectations_dir):
                for askipfile in os.listdir(expectations_dir):
                    if module not in askipfile.lower():
                        continue
                    skip.add_txt(expectations_dir + "/" + askipfile)
            if not skip._trie:
                skip._trie["empty"] = None

            # create test trie
            module_dir = module
            if module == "vk":
                module_dir = "vulkan"
                self.env["EGL_PLATFORM"] = "surfaceless"

            os.chdir(self.build_root + "/opt/deqp/modules/" + module_dir)
            # generate list of tests
            run_batch_command(["./deqp-" + module,
                               "--deqp-runmode=xml-caselist"],
                                 env=self.env)
            outfile = "dEQP-" + module.upper() + "-cases.xml"
            assert(os.path.exists(outfile))
            testlist = DeqpTrie()
            testlist.add_xml(outfile)

            # filter skip trie from testlist trie
            testlist.filter(skip)

            whitelist_txt = None
            if module == "gles2":
                whitelist_txt = pm.project_source_dir("deqp") + "/android/cts/master/gles2-master.txt"
            if module == "gles3":
                whitelist_txt = pm.project_source_dir("deqp") + "/android/cts/master/gles3-master.txt"
            if module == "gles31":
                whitelist_txt = pm.project_source_dir("deqp") + "/android/cts/master/gles31-master.txt"
            if whitelist_txt:
                whitelist_trie = DeqpTrie()
                whitelist_trie.add_txt(whitelist_txt)
                # filter using the deqp whitelist
                testlist.filter_whitelist(whitelist_trie)

            # generate testlist file
            caselist_fn = module + "-cases.txt"
            caselist = open(caselist_fn, "w")
            testlist.write_caselist(caselist)
            caselist.close()
            self.shard_caselist(caselist_fn, o.shard)

        os.chdir(savedir)

        # invoke piglit
        base_options = ("--deqp-log-images=disable "
                        '--deqp-gl-config-name=rgba8888d24s8 '
                        '--deqp-surface-width=400 '
                        '--deqp-surface-height=300 '
                        '--deqp-visibility=hidden '
                        "--deqp-caselist-file=")
        self.env["PIGLIT_DEQP_GLES2_BIN"] = self.build_root + "/opt/deqp/modules/gles2/deqp-gles2"
        self.env["PIGLIT_DEQP_GLES2_EXTRA_ARGS"] =  base_options + self.build_root + "/opt/deqp/modules/gles2/gles2-cases.txt"
        self.env["PIGLIT_DEQP_GLES3_EXE"] = self.build_root + "/opt/deqp/modules/gles3/deqp-gles3"
        self.env["PIGLIT_DEQP_GLES3_EXTRA_ARGS"] = base_options + self.build_root + "/opt/deqp/modules/gles3/gles3-cases.txt"
        self.env["PIGLIT_DEQP_GLES31_BIN"] = self.build_root + "/opt/deqp/modules/gles31/deqp-gles31"
        self.env["PIGLIT_DEQP_GLES31_EXTRA_ARGS"] = base_options + self.build_root + "/opt/deqp/modules/gles31/gles31-cases.txt"
        self.env["PIGLIT_DEQP_VK_BIN"] = self.build_root + "/opt/deqp/modules/vulkan/deqp-vk"
        self.env["PIGLIT_DEQP_VK_EXTRA_ARGS"] = base_options + self.build_root + "/opt/deqp/modules/vulkan/vk-cases.txt" + " --deqp-surface-type=fbo "
        self.env["PIGLIT_DEQP_EGL_BIN"] = self.build_root + "/opt/deqp/modules/egl/deqp-egl"
        self.env["PIGLIT_DEQP_EGL_EXTRA_ARGS"] =  base_options + self.build_root + "/opt/deqp/modules/egl/egl-cases.txt"
        # makes trigonometric functions more accurate with significant
        # performance penalty.  This setting is required to pass
        # several dEQP and vulkan tests.
        self.env["INTEL_PRECISE_TRIG"] = "1"
        self.env["precise_trig"] = "true"
        
        out_dir = self.build_root + "/test/" + o.hardware

        suites = ["deqp_" + m for m in self._modules]
        cmd = [self.build_root + "/bin/piglit",
               "run",
               "-p", "gbm",
               "-o",
               "-b", "junit",
               "--config", conf_file,
               "-c",
               "--junit_suffix", "." + o.hardware + o.arch]

        for test in self.excludes:
            cmd += ["--exclude-tests", test]
        
        run_batch_command(cmd + include_tests + suites + [out_dir],
                             env=self.env,
                             expected_return_code=None,
                             streamedOutput=True)

        single_out_dir = self.build_root + "/../test"
        if not os.path.exists(single_out_dir):
            os.makedirs(single_out_dir)

        basename = "/piglit-deqp"
        if "vulkancts" in pm.current_project():
            basename = "/piglit-deqp-vk"
        filename_components = [basename,
                               o.hardware,
                               o.arch]
        # Uniquely name all test files in one directory, for
        # jenkins
        if o.shard != "0":
            # only put the shard suffix on for non-zero shards.
            # Having _0 suffix interferes with bisection.
            filename_components.append(o.shard)
        final_file = single_out_dir + "_".join(filename_components) + ".xml"

        if not os.path.exists(out_dir + "/results.xml"):
            print "ERROR: no results at " + out_dir + "/results.xml"
        else:
            revisions = RepoSet().branch_missing_revisions()
            print "INFO: filtering tests from " + out_dir + "/results.xml"
            self.filter_tests(revisions,
                              out_dir + "/results.xml",
                              final_file)

            retest = False
            if "bsw" in o.hardware:
                retest = True
            if "hsw" in o.hardware and "vulkancts" in pm.current_project():
                # Bug 95041
                retest = True
            if retest:
                # run piglit again, to eliminate intermittent failures
                tl = TestLister(final_file)
                retests = tl.RetestIncludes(pm.current_project())
                if retests:
                    second_out_dir = out_dir + "/retest"
                    print "WARN: retesting deqp to " + second_out_dir
                    run_batch_command(cmd + retests + suites + [second_out_dir],
                                         env=self.env,
                                         expected_return_code=None,
                                         streamedOutput=True)
                    second_results = TestLister(second_out_dir + "/results.xml")
                    for a_test in tl.TestsNotIn(second_results):
                        print "stripping flaky test: " + a_test.test_name
                        a_test.ForcePass(final_file)
                    rmtree(second_out_dir)

            # create a copy of the test xml in the source root, where
            # jenkins can access it.
            cmd = ["cp", "-a", "-n",
                   self.build_root + "/../test", pm.source_root()]
            run_batch_command(cmd)
            Export().export_tests()

        # run a single piglit test (selected at random) after
        # vulkancts.  This has the side-effect of restoring the
        # default L3 configuration.  The 11.1 stable branch does not
        # restore L3 configuration and fails tests after vulkancts.
        t = PiglitTester(piglit_test="spec.ext.framebuffer.object.getteximage-formats.init-by-clear-and-render.arch")
        if "vulkancts" in pm.current_project():
            t.test()
        check_gpu_hang()
        

    def shard_caselist(self, caselist_fn, shard):
        if shard == "0":
            return

        assert(":" in shard)
        shardargs = shard.split(":")
        shardno = int(shardargs[0])
        shardcount = int(shardargs[1])
        assert(shardno <= shardcount)

        shard_tests = []
        test_no = 0
        test_list = open(caselist_fn).readlines()
        for a_test in test_list:
            if (test_no % shardcount) + 1 == shardno:
                shard_tests.append(a_test)
            test_no = test_no + 1

        rmtree(caselist_fn)
        caselist_fh = open(caselist_fn, "w")
        for a_test in shard_tests:
            caselist_fh.write(a_test)

    def filter_tests(self, revisions, infile, outfile):
        """this method is ripped bleeding from builders.py / PiglitTester"""
        t = ET.parse(infile)
        for a_suite in t.findall("testsuite"):
            # remove skipped tests, which uses ram on jenkins when
            # displaying and provides no value.  
            for a_skip in a_suite.findall("testcase/skipped/.."):
                if a_skip.attrib["status"] in ["crash", "fail"]:
                    continue
                a_suite.remove(a_skip)

            # for each failure, see if there is an entry in the config
            # file with a revision that was missed by a branch
            for afail in a_suite.findall("testcase/failure/..") + a_suite.findall("testcase/error/.."):
                piglit_test = PiglitTest("foo", "foo", afail)
                regression_revision = piglit_test.GetConfRevision()
                abbreviated_revisions = [a_rev[:6] for a_rev in revisions]
                for abbrev_rev in abbreviated_revisions:
                    if abbrev_rev in regression_revision:
                        print "stripping: " + piglit_test.test_name + " " + regression_revision
                        a_suite.remove(afail)
                        # a test may match more than one revision
                        # encoded in a comment
                        break

            # strip any "Suspicious performance behavior failures from
            # dEQP.  We run tests in parallel, and do not expect to
            # have stable performance.
            for afail in a_suite.findall("testcase/failure/.."):
                stdout = afail.find("system-out")
                if stdout is None:
                    continue
                if not stdout.text:
                    continue
                if "Suspicious performance behavior" in stdout.text:
                    stdout.text = stdout.text + "WARN: Intel CI ignores performance failure"
                    for tag in afail.findall("failure"):
                        afail.remove(tag)
                # strip out any failure where a gles3.1 context could not be created.
                if "Warning: Unable to create native OpenGL ES 3.1 context, will use wrapper context." in stdout.text:
                    stdout.text = stdout.text + "\nWARN: Intel CI ignores failures due to dEQP bugs (fdo 95299)\n"
                    for tag in afail.findall("failure"):
                        afail.remove(tag)

            # strip unneeded output from passing tests
            for apass in a_suite.findall("testcase"):
                if apass.attrib["status"] != "pass":
                    continue
                if apass.find("failure") is not None:
                    continue
                out_tag = apass.find("system-out")
                if out_tag is not None:
                    apass.remove(out_tag)
                err_tag = apass.find("system-err")
                if err_tag is not None and err_tag.text is not None:
                    found = False
                    for a_line in err_tag.text.splitlines():
                        m = re.match("pid: ([0-9]+)", a_line)
                        if m is not None:
                            found = True
                            err_tag.text = a_line
                            break
                    if not found:
                        apass.remove(err_tag)
                
        t.write(outfile)
