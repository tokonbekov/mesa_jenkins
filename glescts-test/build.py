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

class GLESCTSTester(object):
    def __init__(self):
        self.o = bs.Options()
        self.pm = bs.ProjectMap()
        self.build_root = self.pm.build_root()
        self.results = bs.DeqpTrie()
        libdir = "x86_64-linux-gnu"
        if self.o.arch == "m32":
            libdir = "i386-linux-gnu"
        self.env = { "LD_LIBRARY_PATH" : self.build_root + "/lib:" + \
                     self.build_root + "/lib/" + libdir + ":" + self.build_root + "/lib/dri",
                     "LIBGL_DRIVERS_PATH" : self.build_root + "/lib/dri",
                     "GBM_DRIVERS_PATH" : self.build_root + "/lib/dri",
                     "INTEL_PRECISE_TRIG" : "1"
        }
        
        if ("hsw" in self.o.hardware or "ivb" in self.o.hardware or "byt" in self.o.hardware):
            self.env["MESA_GLES_VERSION_OVERRIDE"] = "3.1"

        if self._hsw_plus():
            self.env["MESA_GLES_VERSION_OVERRIDE"] = "3.2"
        self.o.update_env(self.env)

        self.whitelists = {
            "ES2-CTS-cases.xml":self.build_root + "/bin/es/cts/gl_cts/data/aosp_mustpass/gles2-master.txt",
            "ES3-CTS-cases.xml":self.build_root + "/bin/es/cts/gl_cts/data/aosp_mustpass/gles3-master.txt",
            "ES31-CTS-cases.xml":self.build_root + "/bin/es/cts/gl_cts/data/aosp_mustpass/gles31-master.txt",
            "ES32-CTS-cases.xml":self.build_root + "/bin/es/cts/gl_cts/data/aosp_mustpass/gles32-master.txt",
            }

    def _hsw_plus(self):
        return ("hsw" in self.o.hardware or
                "skl" in self.o.hardware or
                "bdw" in self.o.hardware or
                "bsw" in self.o.hardware or
                "kbl" in self.o.hardware or
                "bxt" in self.o.hardware)

    def test(self):
        # generate xml files for each suite
        savedir = os.getcwd()
        os.chdir(self.build_root + "/bin/es/cts")
        bs.run_batch_command(["./glcts", "--deqp-runmode=xml-caselist"], env=self.env)

        all_tests = bs.DeqpTrie()
        # filter suites against must pass
        for caselist in glob.glob("*.xml"):
            testlist = bs.DeqpTrie()
            testlist.add_xml(caselist)
            if caselist in self.whitelists:
                whitelist = bs.DeqpTrie()
                whitelist.add_txt(self.whitelists[caselist])
                testlist.filter_whitelist(whitelist)
            # combine test list into single file
            all_tests.merge(testlist)
                
        # filter suites against unstable blacklist
        # TODO(majanes) filter against build type blacklist
        # shard
        shardno = 0
        shardcount = 0
        if self.o.shard != "0":
            shardargs = self.o.shard.split(":")
            shardno = int(shardargs[0])
            shardcount = int(shardargs[1])

        with open("mesa-ci-caselist.txt", "w") as fh:
            all_tests.write_caselist(fh, prefix="", shard=shardno,
                                     shard_count=shardcount)

        shard_tests = bs.DeqpTrie()
        shard_tests.add_txt("mesa-ci-caselist.txt")
        cpus = multiprocessing.cpu_count()
        base_commands = ["./glcts",
                         "--deqp-log-images=disable",
                         "--deqp-gl-config-name=rgba8888d24s8",
                         "--deqp-surface-width=400",
                         "--deqp-surface-height=300",
                         "--deqp-visibility=hidden",
                         "--deqp-crashhandler=enable"]
        procs = {}
        out_fh = open(os.devnull, "w")
        procEnv = dict(os.environ.items() + self.env.items())
        for cpu in range(1, cpus + 1):
            case_fn = "mesa-ci-caselist-" + str(cpu) + ".txt"
            out_fn = "TestResults-" + str(cpu) + ".qpa"
            bs.rmtree(out_fn)
            with open(case_fn, "w") as fh:
                shard_tests.write_caselist(fh, prefix="", shard=cpu,
                                           shard_count=cpus)
            commands = base_commands + ["--deqp-caselist-file=" + case_fn,
                                        "--deqp-log-filename=" + out_fn]
            proc = subprocess.Popen(commands,
                                    stdout=out_fh,
                                    stderr=out_fh,
                                    env=procEnv)
            procs[cpu] = proc
        # invoke tests
        while True:
            time.sleep(1)
            if not procs:
                break
            for cpu, proc in procs.items():
                proc.poll()
                if proc.returncode is None:
                    continue
                
                out_fn = "TestResults-" + str(cpu) + ".qpa"
                case_fn = "mesa-ci-caselist-" + str(cpu) + ".txt"
                test_count = self.results.results_count()
                self.parse_qpa_results(out_fn, pid=proc.pid)
                if test_count == self.results.results_count():
                    # no test executed
                    with open(case_fn, "r") as fh:
                        first_test_name = fh.readline().strip()
                        self.results.add_qpa_blob(first_test_name.split("."),
                                                  '<bogus><Result StatusCode="crash"/></bogus>',
                                                  proc.pid)
                unfinished_tests = bs.DeqpTrie()
                unfinished_tests.add_txt(case_fn)
                unfinished_tests.filter(self.results)
                if (unfinished_tests.empty()):
                    del procs[cpu]
                    continue
                print "WARN: continuing test after crash"
                with open(case_fn, "w") as fh:
                    unfinished_tests.write_caselist(fh)
                bs.rmtree(out_fn)
                proc = subprocess.Popen(base_commands + ["--deqp-caselist-file=" + case_fn,
                                                         "--deqp-log-filename=" + out_fn],
                                        stdout=out_fh,
                                        stderr=out_fh,
                                        env=procEnv)
                procs[cpu] = proc

        os.remove("mesa-ci-caselist.txt")
        os.chdir(savedir)

        out_dir = self.build_root + "/../test"
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        with open(out_dir + "/piglit-glescts-" + self.o.hardware + "-" + self.o.arch + "-" + self.o.shard + ".xml", "w") as of:
            commits = {}
            for commit in bs.RepoSet().branch_missing_revisions():
                commits[str(commit)] = True
            config_file = bs.get_conf_file(self.o.hardware, self.o.arch, project = self.pm.current_project())
            cf = ConfigFilter(config_file, self.o)
            self.results.write_junit(of, cf, commits)

        bs.check_gpu_hang()

        # create a copy of the test xml in the source root, where
        # jenkins can access it.
        cmd = ["cp", "-a", "-n",
               self.build_root + "/../test", self.pm.source_root()]
        bs.run_batch_command(cmd)

        bs.Export().export_tests()

    def parse_qpa_results(self, filename, pid):
        with open(filename, "r") as qpa:
            current_test = ""
            blob = []
            for line in qpa:
                if line.startswith("#beginTestCaseResult"):
                    line = line.strip()
                    current_test = line[len("#beginTestCaseResult "):]
                    continue
                if line.startswith("#endTestCaseResult"):
                    self.results.add_qpa_blob(current_test.split("."), blob, pid)
                    blob = []
                    current_test = ""
                    continue
                if not current_test:
                    continue
                
                blob.append(line)
            if current_test:
                # crashed
                self.results.add_qpa_blob(current_test.split("."), blob, pid)
        
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
