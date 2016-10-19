#!/usr/bin/python
import bz2
import glob
import os
import xml.etree.ElementTree as ET
import xml.sax.saxutils as saxutils

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
        # blacklist can either be a trie or a list of tests
        if list == type(blacklist):
            if not blacklist:
                return
            bltrie = DeqpTrie()
            for test in blacklist:
                bltrie.add_line(test)
            blacklist = bltrie
        
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
        if "*" in whitelist._trie:
            return
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
            if status == "internalerror":
                status = "crash"
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

class ConfigFilter(object):
    """parses config files, to filter out test failures that are not regressions"""
    def __init__(self, file_path, options):
        self._expected_fail = {}
        self._expected_crash = {}
        self._fixed = {}
        self._suffix = options.hardware + options.arch
        with open(file_path, "r") as fh:
            p = CaseConfig(allow_no_value=True)
            p.optionxform = str

            p.readfp(fh)
            if p.has_section("expected-failures"):
                for test, commit in p.items("expected-failures"):
                    self._expected_fail[test] = commit
            if p.has_section("expected-crashes"):
                for test, commit in p.items("expected-crashes"):
                    self._expected_crash[test] = commit
                    assert test not in self._expected_fail
            if p.has_section("fixed-tests"):
                for test, commit in p.items("fixed-tests"):
                    self._fixed[test] = commit
                    assert test not in self._expected_fail
                    assert test not in self._expected_crash

    def write_junit(self, of,
                    suite, test_name, status, duration, stdout, stderr,
                    missing_commits):
        """
        interprets test status with the config, filtering failures for
        tests which have changed status in the missing_commits.
        """
        full_test_name = suite + "." + test_name
        filtered_status = status
        commit_filter = ""
        if full_test_name in self._expected_fail:
            commit_filter = self._expected_fail[full_test_name]
            if status == "fail":
                filtered_status = "skip"
                stdout += "\nWARN: this test failed as expected."
            if status == "crash":
                stdout += "\nWARN: this test crashed when it was expected to fail."
            if status == "pass":
                filtered_status = "fail"
                stdout += "\nWARN: this test passed when it was expected to fail."
            if status == "skip":
                filtered_status = "fail"
                stdout += "\nWARN: this test skipped when it was expected to fail."
        elif full_test_name in self._expected_crash:
            commit_filter = self._expected_crash[full_test_name]
            if status == "crash":
                filtered_status = "skip"
                stdout += "\nWARN: this test crashed as expected."
            if status == "fail":
                stdout += "\nWARN: this test failed when it was expected to crash."
            if status == "pass":
                filtered_status = "fail"
                stdout += "\nWARN: this test passed when it was expected to crash."
            if status == "skip":
                filtered_status = "fail"
                stdout += "\nWARN: this test skipped when it was expected to crash."
        elif full_test_name in self._fixed:
            commit_filter = self._fixed[full_test_name]

        for word in commit_filter.split():
            if word in missing_commits:
                stdout += "\nWARN: this test had status " + status + \
                          " but changed in " + commit_filter
                filtered_status = "skip"
                break

        if status == "skip" and filtered_status == "skip":
            return
        
        # status attrib gets the "real" status of the test.  filtering
        # based on config changes whether the tag has a <failure> or
        # <skipped> subtag, which is how jenkins reports results.  We
        # need the "real" test status for handling bisection.
        of.write("""  <testcase classname="{}" name="{}" status="{}" time="{}">\n""".format(suite,
                                                                                            test_name + "." + self._suffix,
                                                                                            status,
                                                                                            duration))
        if filtered_status == "skip":
            of.write("""   <skipped type="skip"/>\n""")
        if filtered_status == "fail":
            of.write("""   <failure type="fail"/>\n""")
        if stdout:
            of.write("""   <system-out>{}</system-out>\n""".format(saxutils.escape(stdout)))
        if stderr:
            of.write("""   <system-err>{}</system-err>\n""".format(saxutils.escape(stderr)))
        of.write("""  </testcase>\n""")

class DeqpTester:
    def __init__(self):
        self.o = Options()
        self.pm = ProjectMap()

    def test(self, binary, list_policy, extra_args=None, env=None):
        if extra_args is None:
            extra_args = []
        if env == None:
            env = {}
        build_root = self.pm.build_root()
        libdir = "x86_64-linux-gnu"
        if self.o.arch == "m32":
            libdir = "i386-linux-gnu"
        base_env = { "LD_LIBRARY_PATH" : build_root + "/lib:" + \
                     build_root + "/lib/" + libdir + ":" + build_root + "/lib/dri",
                     "LIBGL_DRIVERS_PATH" : build_root + "/lib/dri",
                     "INTEL_PRECISE_TRIG" : "1",
                     "GBM_DRIVERS_PATH" : build_root + "/lib/dri"}
        for k,v in base_env.items():
            env[k] = v
        self.o.update_env(env)
        all_tests = DeqpTrie()
        if self.o.retest_path:
            testlist = TestLister(self.o.retest_path + "/test/")
            include_tests = testlist.RetestIncludes(self.pm.current_project())
            if not include_tests:
                # we were supposed to retest failures, but there were none
                return all_tests
            with open("retest_caselist.txt", "w") as fh:
                for t in include_tests:
                    fh.write(t)
                    fh.write("\n")
            all_tests.add_txt("retest_caselist.txt")
        else:
            all_tests = list_policy.tests(env)

        list_policy.blacklist(all_tests)
        
        if all_tests.empty():
            return all_tests

        shardno = 0
        shardcount = 0
        if self.o.shard != "0":
            shardargs = self.o.shard.split(":")
            shardno = int(shardargs[0])
            shardcount = int(shardargs[1])

        savedir = os.getcwd()
        os.chdir(os.path.dirname(binary))
        with open("mesa-ci-caselist.txt", "w") as fh:
            all_tests.write_caselist(fh, prefix="", shard=shardno,
                                     shard_count=shardcount)

        shard_tests = DeqpTrie()
        shard_tests.add_txt("mesa-ci-caselist.txt")

        cpus = multiprocessing.cpu_count()
        base_commands = [binary,
                         "--deqp-log-images=disable",
                         "--deqp-gl-config-name=rgba8888d24s8",
                         "--deqp-surface-width=400",
                         "--deqp-surface-height=300",
                         "--deqp-visibility=hidden"] + extra_args
        procs = {}
        out_fh = open(os.devnull, "w")
        procEnv = dict(os.environ.items() + env.items())
        single_proc = False
        if "DEQP_DETECT_GPU_HANG" in env:
            single_proc = True
        for cpu in range(1, cpus + 1):
            case_fn = "mesa-ci-caselist-" + str(cpu) + ".txt"
            out_fn = "TestResults-" + str(cpu) + ".qpa"
            if os.path.exists(out_fn):
                os.remove(out_fn)
            with open(case_fn, "w") as fh:
                shard_tests.write_caselist(fh, prefix="", shard=cpu,
                                           shard_count=cpus)

            # do not execute deqp if no tests have been scheduled for
            # the current cpu core
            core_tests = DeqpTrie()
            core_tests.add_txt(case_fn)
            if core_tests.empty():
                continue
            
            commands = base_commands + ["--deqp-caselist-file=" + case_fn,
                                        "--deqp-log-filename=" + out_fn]
            test_name = ""
            if single_proc:
                with open(case_fn, "r") as fh:
                    test_name = fh.readline().strip()
                    commands = base_commands + ["-n", test_name,
                                                "--deqp-log-filename=" + out_fn]
            proc = subprocess.Popen(commands,
                                    stdout=out_fh,
                                    stderr=out_fh,
                                    env=procEnv)
            if single_proc:
                print str(proc.pid) + ": " + test_name

            procs[cpu] = proc

        results = DeqpTrie()
        # invoke tests
        while True:
            if not single_proc:
                time.sleep(1)
            if not procs:
                break
            for cpu, proc in procs.items():
                proc.poll()
                if proc.returncode is None:
                    continue
                
                out_fn = "TestResults-" + str(cpu) + ".qpa"
                case_fn = "mesa-ci-caselist-" + str(cpu) + ".txt"
                test_count = results.results_count()
                self.parse_qpa_results(results, out_fn, pid=proc.pid)
                if test_count == results.results_count():
                    # no test executed
                    with open(case_fn, "r") as fh:
                        first_test_name = fh.readline().strip()
                        results.add_qpa_blob(first_test_name.split("."),
                                                  '<bogus><Result StatusCode="crash"/></bogus>',
                                                  proc.pid)
                unfinished_tests = DeqpTrie()
                unfinished_tests.add_txt(case_fn)
                unfinished_tests.filter(results)
                if (unfinished_tests.empty()):
                    del procs[cpu]
                    continue
                if not single_proc:
                    print "WARN: continuing test after crash"
                with open(case_fn, "w") as fh:
                    unfinished_tests.write_caselist(fh)
                if os.path.exists(out_fn):
                    os.remove(out_fn)
                commands = base_commands + ["--deqp-caselist-file=" + case_fn,
                                            "--deqp-log-filename=" + out_fn]
                test_name = ""
                if single_proc:
                    with open(case_fn, "r") as fh:
                        test_name = fh.readline().strip()
                        commands = base_commands + ["-n", test_name,
                                                    "--deqp-log-filename=" + out_fn]
                proc = subprocess.Popen(commands,
                                        stdout=out_fh,
                                        stderr=out_fh,
                                        env=procEnv)
                if single_proc:
                    print str(proc.pid) + ": " + test_name
                procs[cpu] = proc

        os.remove("mesa-ci-caselist.txt")
        os.chdir(savedir)
        return results
        
    def parse_qpa_results(self, results_trie, filename, pid):
        with open(filename, "r") as qpa:
            current_test = ""
            blob = []
            for line in qpa:
                if line.startswith("#beginTestCaseResult"):
                    line = line.strip()
                    current_test = line[len("#beginTestCaseResult "):]
                    continue
                if line.startswith("#endTestCaseResult"):
                    results_trie.add_qpa_blob(current_test.split("."), blob, pid)
                    blob = []
                    current_test = ""
                    continue
                if not current_test:
                    continue
                
                blob.append(line)
            if current_test:
                # crashed
                results_trie.add_qpa_blob(current_test.split("."), blob, pid)

    def generate_results(self, results_trie, config_policy):
        out_dir = self.pm.build_root() + "/../test"
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        with open(out_dir + "/piglit-" + self.pm.current_project() + "-" + self.o.hardware + "-" + self.o.arch + "-" + self.o.shard + ".xml", "w") as of:
            commits = {}
            for commit in RepoSet().branch_missing_revisions():
                commits[str(commit)] = True
            results_trie.write_junit(of, config_policy, commits)

        check_gpu_hang()

        # create a copy of the test xml in the source root, where
        # jenkins can access it.
        cmd = ["cp", "-a", "-n",
               self.pm.build_root() + "/../test", self.pm.source_root()]
        run_batch_command(cmd)

        Export().export_tests()


    def build(self):
        pass
    def clean(self):
        pass

def generation(options):
        if "skl" in options.hardware or "kbl" in options.hardware or "bxt" in options.hardware:
            return 9.0
        if "bdw" in options.hardware or "bsw" in options.hardware:
            return 8.0
        if "hsw" in options.hardware:
            return 7.5
        if "ivb" in options.hardware or "byt" in options.hardware:
            return 7.0
        if "snb" in options.hardware:
            return 6.0
        if "ilk" in options.hardware:
            return 5.0
        assert("g965" in options.hardware or "g33" in options.hardware or "g45" in options.hardware)
        return 4.0

class CtsTestList(object):
    def __init__(self):
        self.pm = ProjectMap()
        self.o = Options()

    def tests(self, env=None):
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
        if env is None:
            libdir = "x86_64-linux-gnu"
            if self.o.arch == "m32":
                libdir = "i386-linux-gnu"
            env = {"MESA_GLES_VERSION_OVERRIDE" : "3.2",
                   "LD_LIBRARY_PATH" : br + "/lib:" + \
                   br + "/lib/" + libdir + ":" + br + "/lib/dri",
                   "LIBGL_DRIVERS_PATH" : br + "/lib/dri"}
            self.o.update_env(env)

        save_override = env["MESA_GLES_VERSION_OVERRIDE"]
        env["MESA_GLES_VERSION_OVERRIDE"] = "3.2"
        cmd = [binary,
               "--deqp-runmode=xml-caselist"]
        run_batch_command(cmd, env=env)
        env["MESA_GLES_VERSION_OVERRIDE"] = save_override
        all_tests = DeqpTrie()
        for caselist in glob.glob("*.xml"):
            testlist = DeqpTrie()
            testlist.add_xml(caselist)
            if caselist in whitelists:
                whitelist = DeqpTrie()
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
        blacklist = DeqpTrie()
        if "bxt" in self.o.hardware:
            blacklist_dir = self.pm.project_source_dir("prerelease") + "/" + project + "/"
        blacklist_file = blacklist_dir + self.o.hardware + self.o.arch + "_blacklist.txt"
        if os.path.exists(blacklist_file):
            blacklist.add_txt(blacklist_file)
        blacklist_file = blacklist_dir + self.o.hardware + "_blacklist.txt"
        if os.path.exists(blacklist_file):
            blacklist.add_txt(blacklist_file)
        blacklist_file = blacklist_dir + self.o.hardware[:3] + "_blacklist.txt"
        if os.path.exists(blacklist_file):
            blacklist.add_txt(blacklist_file)
        all_tests.filter(blacklist)
        version = mesa_version()
        unsupported = []
        if "11.2" in version:
            unsupported = ["ES32-CTS"]
            if generation(self.o) < 8.0:
                unsupported.append("ES31-CTS")
            if generation(self.o) < 6.0:
                unsupported.append("ES30-CTS")

        if "12.0" in version:
            if generation(self.o) < 8.0:
                unsupported.append("ES31-CTS")

        all_tests.filter(unsupported)        

