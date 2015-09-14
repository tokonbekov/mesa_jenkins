import multiprocessing
import os
import re
import socket
import subprocess
import sys
import urllib2
import xml.etree.ElementTree as ET
from . import Options
from . import ProjectMap
from . import run_batch_command
from . import rmtree
from . import Export
from . import GTest
from . import RepoSet
from . import PiglitTest
from . import ProjectInvoke
from . import Jenkins
from . import RevisionSpecification
from . import get_conf_file
from . import TestLister
from . import NoConfigFile

def cpu_count():
    cpus = multiprocessing.cpu_count() + 1
    if cpus > 18:
        cpus = 18
    return cpus

def get_package_config_path():
    lib_dir = ""
    if Options().arch == "m32":
        lib_dir = "i386-linux-gnu"
    else:
        lib_dir = "x86_64-linux-gnu"

    build_root = ProjectMap().build_root()
    pkg_config_path = build_root + "/lib/" + lib_dir + "/pkgconfig:" + \
                      build_root + "/lib/pkgconfig:" + \
                      "/usr/lib/"+ lib_dir + "/pkgconfig:" + \
                      "/usr/lib/pkgconfig"
    return pkg_config_path

def delete_src_pyc(path):
    for dirpath, _, filenames in os.walk(path):
        for each_file in filenames:
            if each_file.endswith('.pyc'):
                if os.path.exists(os.path.join(dirpath, each_file)):
                    os.remove(os.path.join(dirpath, each_file))

def git_clean(src_dir):
    savedir = os.getcwd()
    os.chdir(src_dir)
    run_batch_command(["git", "clean", "-xfd"])
    run_batch_command(["git", "reset", "--hard", "HEAD"])
    os.chdir(savedir)
                    
class AutoBuilder(object):

    def __init__(self, o=None, configure_options=None, export=True,
                 opt_flags=""):
        self._options = o
        self._tests = None
        self._export = export
        self._opt_flags = opt_flags

        self._configure_options = configure_options
        if not configure_options:
            self._configure_options = []

        if not o:
            self._options = Options()

        self._project_map = ProjectMap()
        project = self._project_map.current_project()
        self._project = project

        self._src_dir = self._project_map.project_source_dir(project)
        self._build_root = self._project_map.build_root()
        self._build_dir = "/tmp/" + project + "/build_" + self._options.arch

    def build(self):
        if not os.path.exists(self._build_root):
            os.makedirs(self._build_root)
        if not os.path.exists(self._build_dir):
            os.makedirs(self._build_dir)

        optflags = self._opt_flags
        if self._options.config != "debug":
            optflags = "-O2 -DNDEBUG"
            
        savedir = os.getcwd()
        pkg_config = get_package_config_path()
        os.chdir(self._build_dir)
        flags = []
        if self._options.arch == "m32":
            flags = ["CFLAGS=-m32 -D_GLIBCXX_USE_CXX11_ABI=0 " + optflags,
                     "CXXFLAGS=-m32 -D_GLIBCXX_USE_CXX11_ABI=0 " + optflags, 
                     "--enable-32-bit",
                     "--host=i686-pc-linux-gnu"]
        else:
            flags = ["CFLAGS=-m64 -D_GLIBCXX_USE_CXX11_ABI=0 " + optflags,
                     "CXXFLAGS=-m64 -D_GLIBCXX_USE_CXX11_ABI=0 " + optflags]

        os.chdir(self._src_dir)
        run_batch_command(["autoreconf", "--verbose", "--install", "-s"])
        os.chdir(self._build_dir)
        run_batch_command([self._src_dir + "/configure", 
                           "PKG_CONFIG_PATH=" + pkg_config, 
                           "CC=ccache gcc -" + self._options.arch, 
                           "CXX=ccache g++ -" + self._options.arch, 
                           "--prefix=" + self._build_root] + \
                          flags + self._configure_options)

        run_batch_command(["make",  "-j", 
                           str(cpu_count())])
        run_batch_command(["make",  "install"])

        os.chdir(savedir)

        if self._export:
            Export().export()

    def AddGtests(self, tests):
        self._tests = GTest(binary_dir = self._build_dir, executables=tests)

    def test(self):
        savedir = os.getcwd()
        os.chdir(self._build_dir)

        try:
            run_batch_command(["make",  "-k", "-j", 
                               str(cpu_count()),
                               "check"])
        except(subprocess.CalledProcessError):
            print "WARN: make check failed"
            os.chdir(savedir)
            # bug 91773
            # Export().create_failing_test(self._project +
            #                              "-make-check-failure", "")
        os.chdir(savedir)

        if self._tests:
            self._tests.run_tests()

        if self._export:
            Export().export()

    def clean(self):
        git_clean(self._src_dir)
        rmtree(self._build_dir)
        assert(not os.path.exists(self._build_dir))

class CMakeBuilder(object):
    def __init__(self, extra_definitions=None):
        self._options = Options()
        self._project_map = ProjectMap()

        if not extra_definitions:
            extra_definitions = []
        self._extra_definitions = extra_definitions

        project = self._project_map.current_project()

        self._src_dir = self._project_map.project_source_dir(project)
        self._build_root = self._project_map.build_root()
        self._build_dir = self._src_dir + "/build_" + self._options.arch

    def build(self):

        if not os.path.exists(self._build_dir):
            os.makedirs(self._build_dir)

        savedir = os.getcwd()
        os.chdir(self._build_dir)

        cflag = "-m32 -D_GLIBCXX_USE_CXX11_ABI=0"
        cxxflag = "-m32 -D_GLIBCXX_USE_CXX11_ABI=0"
        if self._options.arch == "m64":
            cflag = "-m64 -D_GLIBCXX_USE_CXX11_ABI=0"
            cxxflag = "-m64 -D_GLIBCXX_USE_CXX11_ABI=0"
        run_batch_command(["cmake", self._src_dir, 
                           "-DCMAKE_INSTALL_PREFIX:PATH=" + self._build_root] \
                          + self._extra_definitions,
                          env={"PKG_CONFIG_PATH" : get_package_config_path(),
                               "CC":"ccache gcc",
                               "CXX":"ccache g++",
                               "CFLAGS":cflag,
                               "CXXFLAGS":cxxflag})

        run_batch_command(["cmake", "--build", self._build_dir,
                           "--", "-j" + str(cpu_count())])
        run_batch_command(["make", "install"])

        os.chdir(savedir)

        Export().export()

    def clean(self):
        git_clean(self._src_dir)
        rmtree(self._build_dir)
        assert(not os.path.exists(self._build_dir))
        
    def test(self):
        savedir = os.getcwd()
        os.chdir(self._build_dir)

        # get test names
        command = ["ctest", "-V", "-N"]
        (out, _) = run_batch_command(command, streamedOutput=False, quiet=True)

        os.chdir(savedir)

        out = out.splitlines()
        for aline in out:
            # execute each command reported by ctest
            match = re.match(".*Test command: (.*)", aline)
            if not match:
                continue
            (bin_dir, exe) = os.path.split(match.group(1))
            #bs.GTest(bin_dir, exe, working_dir=bin_dir).run_tests()
    
class PiglitTester(object):
    def __init__(self, _suite="quick", device_override=None, piglit_test=None):
        self.device_override = device_override
        self._piglit_test = None
        if piglit_test:
            # drop the hw/arch suffix
            self._piglit_test = ".".join(piglit_test.split(".")[:-1])

        o = Options()
        self.suite = _suite

        # in bisect or single_test, a test may be in either the cpu or gpu suite.
        # use the quick suite, which is more comprehensive
        if o.retest_path:
            self.suite = "quick"
        if piglit_test:
            self.suite = "quick"

        pm = ProjectMap()
        self.build_root = pm.build_root()
        libdir = "x86_64-linux-gnu"
        if o.arch == "m32":
            libdir = "i386-linux-gnu"
        self.env = { "LD_LIBRARY_PATH" : self.build_root + "/lib:" + \
                self.build_root + "/lib/" + libdir + ":" + \
                self.build_root + "/lib/dri:" + \
                self.build_root + "/lib/piglit/lib",

                "LIBGL_DRIVERS_PATH" : self.build_root + "/lib/dri",
                "GBM_DRIVERS_PATH" : self.build_root + "/lib/dri",
                # fixes dxt subimage tests that fail due to a
                # combination of unreasonable tolerances and possibly
                # bugs in debian's s2tc library.  Recommended by nroberts
                "S2TC_DITHER_MODE" : "NONE",

                # In the event of a piglit related bug, we want the backtrace
                "PIGLIT_DEBUG": "1",
        }

    def test(self):
        pm = ProjectMap()
        o = Options()

        mesa_version = self.mesa_version()
        if o.hardware == "bsw" or "skl" in o.hardware:
            if "10.5" in mesa_version or "10.6" in mesa_version:
                print "WARNING: piglit hangs on bsw for stable mesa"
                return

        dev_ids = { "byt" : "0x0F32",
                    "g45" : "0x2E22",
                    "g965" : "0x29A2",
                    "ilk" : "0x0042",
                    "ivbgt2" : "0x0162",
                    "snbgt2" : "0x0122",
                    "hswgt3" : "0x042A",
                    "bdwgt2" : "0x161E",
                    "chv" : "0x22B0",
                    "sklgt3" : "0x192B",
                    "bsw" : "0x22B1",
        }
        if self.device_override:
            self.env["INTEL_DEVID_OVERRIDE"] = dev_ids[self.device_override]

        out_dir = self.build_root + "/test/" + o.hardware

        hardware = o.hardware
        if self.device_override:
            hardware = self.device_override

        try:
            conf_file = get_conf_file(hardware, o.arch)
        except NoConfigFile:
            print >>sys.stderr, 'No config file found for hardware: {0} arch: {1}'.format(
                hardware, o.arch)
            sys.exit(1)
        
        suffix = o.hardware
        hardware = o.hardware
        if self.device_override:
            suffix = self.device_override
            hardware = self.device_override
        cmd = [self.build_root + "/bin/piglit",
               "run",
               "-p", "gbm",
               "-b", "junit",
               "--junit_suffix", "." + suffix + o.arch,

               # intermittently fails snb?
               "--exclude-tests", "timestamp-get",
               "--exclude-tests", "glsl-routing",

               # fails intermittently
               "--exclude-tests", "ext_timer_query",
               "--exclude-tests", "arb_timer_query",

               # crashes intermittently, or at least Dylan's tracking
               # reports "Incomplete run"
               # TODO: write bug
               "--exclude-tests", "spec.khr_debug.object-label_gl",

               # fails intermittently on bdw, byt, and bsw
               # Bug 91017
               "--exclude-tests", "arb_framebuffer_no_attachments.arb_framebuffer_no_attachments-atomic",
               
               # fails intermittently on g45, fails reliably on all
               # others.  Test introduced Oct 2014
               "--exclude-tests", "vs-float-main-return"]

        if os.path.exists(conf_file):
            cmd = cmd + ["--config", conf_file]

        # intermittent on at least snbgt1
        exclude_tests = ["glsl-1_10.execution.vs-vec2-main-return"]

        # Bug 90407
        exclude_tests = exclude_tests + ["shaders.glsl-fs-vec4-indexing-temp-dst",
                                         "shaders.glsl-fs-vec4-indexing-temp-src-in-nested-loop-outer"]

        # TODO: bisect these intermittent failures and write bugs
        exclude_tests = exclude_tests + ["arb_separate_shader_objects.validateprogrampipeline",
                                         "glsl-1_50.execution.geometry.clip-distance",
                                         "glsl-1_50.execution.gs-redeclares-pervertex-out-only",
                                         "glsl-1_50.execution.redeclare-pervertex-subset-vs-to-gs",
                                         "glsl-1_50.transform-feedback-type-and-size"]

        if "snb" in hardware:
            # hangs snb
            exclude_tests = exclude_tests + ["triangle_strip_adjacency"]
            
        if "ivb" in hardware or "byt" in hardware:
            # Bug 91718
            exclude_tests = exclude_tests + ["arb.shader.image.load.store.invalid"]

        if "hsw" in hardware:
            # intermittent on haswell bug 89219 fixed in 10c82c6c5fc415d323a5e9c6acdc6a4c85d6b712
            # exclude_tests = exclude_tests + ["arb_uniform_buffer_object.bufferstorage"]

            # bug: 91301
            exclude_tests = exclude_tests + ["spec.arb_gpu_shader5.arb_gpu_shader5-emitstreamvertex_nodraw"]

        if "g965" in hardware:
            # intermittent GPU hang on g965
            exclude_tests = exclude_tests + ["arb_shader_texture_lod.execution.tex-miplevel-selection",
                                             # fdo Bug 89398
                                             "glsl-1_20.execution.clipping.fixed-clip-enables",
                                             "glsl-1_10.execution.clipping.clip-plane-transformation pos_clipvert"]

        if "bdw" in hardware:
            # many tests match this string and are intermittent on
            # bdw.  This appears to be resolved by the update to linux
            # kernel 4.0
            #exclude_tests = exclude_tests + ["arb_texture_multisample.texelFetch.fs.sampler2dms"]

            # TODO: write bug for
            exclude_tests = exclude_tests + ["variable-indexing.vs-output-array-vec4-index-wr-before-gs"]

            # bug: 91298
            exclude_tests = exclude_tests + ['piglit.spec.arb_shader_atomic_counters.unused-result',
                                             # bug 91611
                                             "arb_shader_image_load_store.execution.basic-imagestore-from-uniform",
                                             "arb_shader_image_load_store.host-mem-barrier"]
        
        if "byt" in hardware:
            # bug 89219, fixed in 10c82c6c5fc415d323a5e9c6acdc6a4c85d6b712
            # exclude_tests = exclude_tests + ["arb_uniform_buffer_object.bufferstorage"]
            pass

        if "skl" in hardware:
            # hard hangs skl
            exclude_tests = exclude_tests + ["fbo-depth-array"]
            exclude_tests = exclude_tests + ["ext_framebuffer_multisample.no-color"]
            # intermittent, bug 91926
            exclude_tests = exclude_tests + ["spec.arb_pixel_buffer_object.texsubimage.pbo"]

        if "bsw" in hardware:
            # TODO: write bug
            exclude_tests = exclude_tests + ["glsl-3_30.execution.built-in-functions.fs-floatbitstouint",
                                             # bug 91611
                                             "arb_shader_image_load_store.execution.basic-imagestore-from-uniform",
                                             "arb_shader_image_load_store.host-mem-barrier"]

        for test in exclude_tests:
            fixed_test = test.replace('_', '.')
            fixed_test = fixed_test.replace(' ', '.')
            cmd = cmd + ["--exclude-tests", fixed_test]

        if o.retest_path:
            # only test items which previously failed
            include_tests = []
            testlist = TestLister(o.retest_path + "/test/")
            for atest in testlist.Tests():
                test_name_good_chars = re.sub('[_ !:=]', ".", atest.test_name)
                # drop the spec
                test_name = ".".join(test_name_good_chars.split(".")[1:])
                include_tests = include_tests + ["--include-tests", test_name]
            if not include_tests:
                # we were supposed to retest failures, but there were none
                return
            cmd = cmd + include_tests

        if self._piglit_test:
            # support for running a single test
            cmd = cmd + ["--include-tests", self._piglit_test]
            
        concurrency_options = ["-c"]
        cmd = cmd + concurrency_options
            
        cmd = cmd + [self.suite,
                     out_dir ]

        streamedOutput = True
        if o.retest_path:
            streamedOutput = False
        (out, err) = run_batch_command(cmd, env=self.env,
                                       expected_return_code=None,
                                       streamedOutput=streamedOutput)
        if err and "There are no tests scheduled to run" in err:
            open(out_dir + "/results.xml", "w").write("<testsuites/>")

        single_out_dir = self.build_root + "/../test"
        if not os.path.exists(single_out_dir):
            os.makedirs(single_out_dir)

        if os.path.exists(out_dir + "/results.xml"):
            # obtain the set of revisions on master which are not on
            # the current branches.  This set represents the revisions
            # that should cause tests to be disregared.
            revisions = RepoSet().branch_missing_revisions()
            print "INFO: filtering tests from " + out_dir + "/results.xml"
            # Uniquely name all test files in one directory, for
            # jenkins
            self.filter_tests(revisions,
                              out_dir + "/results.xml",
                              single_out_dir + "_".join(["/" + pm.current_project(),
                                                         hardware,
                                                         o.arch]) + ".xml")

        # create a copy of the test xml in the source root, where
        # jenkins can access it.
        cmd = ["cp", "-a", "-n",
               self.build_root + "/../test", pm.source_root()]
        run_batch_command(cmd)

        Export().export_tests()
        self.check_gpu_hang()

    def filter_tests(self, revisions, infile, outfile):
        """this functionality has been duplicated in deqp-test/build.py.  If
        it needs to change, then either change it everywhere or refactor out
        the duplication."""
        t = ET.parse(infile)
        r = t.getroot()
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
                
        t.write(outfile)

    def check_gpu_hang(self):
        # some systems have a gpu hang watchdog which reboots
        # machines, and others do not.   This method checks dmesg,
        # produces a failing test if a hang is found, and schedules a
        # reboot if the host is determined to be a jenkins builder
        # (user=jenkins)
        (out, _) = run_batch_command(["dmesg"], quiet=True,
                                     streamedOutput=False)
        hang_text = ""
        for a_line in out.split('\n'):
            if "gpu hang" in a_line.lower():
                hang_text = a_line
                break

        if not hang_text:
            return

        hostname = socket.gethostname()
        Export().create_failing_test("gpu-hang-" + hostname,
                                     hang_text)
        # trigger reboot
        if ('otc-gfxtest-' in hostname):
            label = hostname[len('otc-gfxtest-'):]
            o = Options()
            o.hardware = label
            reboot_invoke = ProjectInvoke(options=o, project="reboot-slave")
            reboot_invoke.set_info("status", "rebuild")
            try:
                Jenkins(RevisionSpecification(),
                        Options().result_path).reboot_builder(label)
            except(urllib2.URLError):
                print "ERROR: encountered error triggering reboot"

    def mesa_version(self):
        (out, _) = run_batch_command([self.build_root + "/bin/wflinfo",
                                      "--platform=gbm", "-a", "gl"],
                                     streamedOutput=False,
                                     env=self.env)
        for a_line in out.splitlines():
            if "OpenGL version string" not in a_line:
                continue
            tokens = a_line.split(":")
            assert len(tokens) == 2
            version_string = tokens[1].strip()
            version_tokens = version_string.split()
            assert len(version_tokens) >= 3
            return version_tokens[2]

    def build(self):
        pass

    def clean(self):
        pass
