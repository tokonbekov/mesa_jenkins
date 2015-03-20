import os, multiprocessing, re, subprocess
import socket
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

class AutoBuilder(object):

    def __init__(self, o=None, configure_options=None, export=True):
        self._options = o
        self._tests = None
        self._export = export

        self._configure_options = configure_options
        if not configure_options:
            self._configure_options = []

        if not o:
            self._options = Options()
            
        self._project_map = ProjectMap()
        project = self._project_map.current_project()

        self._src_dir = self._project_map.project_source_dir(project)
        self._build_root = self._project_map.build_root()
        self._build_dir = self._src_dir + "/build_" + self._options.arch

    def build(self):
        if not os.path.exists(self._build_root):
            os.makedirs(self._build_root)
        if not os.path.exists(self._build_dir):
            os.makedirs(self._build_dir)

        optflags = ""
        if self._options.config != "debug":
            optflags = " -O2 -DNDEBUG"
            
        savedir = os.getcwd()
        os.chdir(self._build_dir)
        flags = []
        if self._options.arch == "m32":
            flags = ["CFLAGS=-m32" + optflags,
                     "CXXFLAGS=-m32" + optflags, 
                     "--enable-32-bit",
                     "--host=i686-pc-linux-gnu"]
        else:
            flags = ["CFLAGS=-m64" + optflags,
                     "CXXFLAGS=-m64" + optflags]

        run_batch_command(["../autogen.sh", 
                           "PKG_CONFIG_PATH=" + get_package_config_path(), 
                           "CC=ccache gcc -" + self._options.arch, 
                           "CXX=ccache g++ -" + self._options.arch, 
                           "--prefix=" + self._build_root] + \
                          flags + self._configure_options)

        run_batch_command(["make",  "-j", 
                           str(multiprocessing.cpu_count() + 1)])
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
                               str(multiprocessing.cpu_count() + 1),
                               "check"])
        except(subprocess.CalledProcessError):
            print "WARN: make check failed"

        if self._tests:
            self._tests.run_tests()

        if self._export:
            Export().export()

        os.chdir(savedir)

    def clean(self):
        savedir = os.getcwd()
        if not os.path.exists(self._build_dir):
            return
        os.chdir(self._build_dir)
        if os.path.exists("Makefile"):
            try:
                run_batch_command(["make", "distclean"])
            except(subprocess.CalledProcessError):
                pass
        os.chdir(savedir)
        if os.path.exists(self._build_dir):
            rmtree(self._build_dir)

        delete_src_pyc(self._src_dir)


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

        cflag = "-m32"
        cxxflag = "-m32"
        if self._options.arch == "m64":
            cflag = "-m64"
            cxxflag = "-m64"
        run_batch_command(["cmake", self._src_dir, 
                           "-DCMAKE_INSTALL_PREFIX:PATH=" + self._build_root] \
                          + self._extra_definitions,
                          env={"PKG_CONFIG_PATH" : get_package_config_path(),
                               "CC":"ccache gcc",
                               "CXX":"ccache g++",
                               "CFLAGS":cflag,
                               "CXXFLAGS":cxxflag})

        run_batch_command(["cmake", "--build", self._build_dir,
                           "--", "-j" + str(multiprocessing.cpu_count() + 1)])
        run_batch_command(["make", "install"])

        os.chdir(savedir)

        Export().export()

    def clean(self):
        if os.path.exists(self._build_dir):
            rmtree(self._build_dir)

        delete_src_pyc(self._src_dir)
        
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
    def __init__(self, _piglit_test=None, _suite="quick", device_override=None, nir=False):
        self.piglit_test = _piglit_test
        self.suite = _suite
        self.device_override = device_override
        self.nir = nir

    def test(self):
        pm = ProjectMap()
        br = pm.build_root()
        o = Options()

        libdir = "x86_64-linux-gnu"
        if o.arch == "m32":
            libdir = "i386-linux-gnu"
            
        env = { "LD_LIBRARY_PATH" : br + "/lib:" + \
                br + "/lib/" + libdir + ":" + \
                br + "/lib/dri:" + \
                br + "/lib/piglit/lib",

                "LIBGL_DRIVERS_PATH" : br + "/lib/dri",
                "GBM_DRIVERS_PATH" : br + "/lib/dri",
                # fixes dxt subimage tests that fail due to a
                # combination of unreasonable tolerances and possibly
                # bugs in debian's s2tc library.  Recommended by nroberts
                "S2TC_DITHER_MODE" : "NONE"
        }
        if self.nir:
            env["INTEL_USE_NIR"] = "1"

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
        }
        if self.device_override:
            env["INTEL_DEVID_OVERRIDE"] = dev_ids[self.device_override]

        out_dir = br + "/test/" + o.hardware

        hardware_conf = o.hardware
        if self.device_override:
            hardware_conf = self.device_override

        if "snb" in hardware_conf:
            hardware_conf = "snb"
        if "ivb" in hardware_conf:
            hardware_conf = "ivb"
        if "bdw" in hardware_conf:
            hardware_conf = "bdw"
        if "hsw" in hardware_conf:
            hardware_conf = "hsw"
        if "skl" in hardware_conf:
            hardware_conf = "skl"

        # all platforms other than g965 have separate 32-bit failures
        if hardware_conf not in ["g965", "g33", "g45", "ilk", "chv", "skl"]:
            if o.arch == "m32":
                hardware_conf = hardware_conf + "m32"
        hardware_conf = pm.source_root() + "/piglit-test" + \
                        "/" + hardware_conf + ".conf"

        suffix = o.hardware
        if self.device_override:
            suffix = self.device_override
        if self.nir:
            suffix = "nir_" + suffix
        cmd = [br + "/bin/piglit",
               "run",
               "-p", "gbm",
               "-b", "junit",
               "-c",
               "--junit_suffix", "." + suffix + o.arch,

               # intermittently fails snb?
               "--exclude-tests", "timestamp-get",
               "--exclude-tests", "glsl-routing",

               # fails intermittently
               "--exclude-tests", "ext_timer_query",
               "--exclude-tests", "arb_timer_query",

               # fails intermittently on g45, fails reliably on all
               # others.  Test introduced Oct 2014
               "--exclude-tests", "vs-float-main-return"]

        if os.path.exists(hardware_conf):
            cmd = cmd + ["--config", hardware_conf]

        # intermittent on at least snbgt1 and nir hswgt3e
        exclude_tests = ["glsl-1_10.execution.vs-vec2-main-return"]

        # this occured intermittently on hsw, ivb and others 2/19 -
        # 2/23.  Bisect takes 3 minutes to run the test.  It is very
        # infrequent.
        # Matt improved the runtime of this test by 80%
        # exclude_tests = ["ext_transform_feedback.max-varyings"]

        if "snb" in o.hardware:
            # hangs snb
            exclude_tests = exclude_tests + ["triangle_strip_adjacency"]

        if "hsw" in o.hardware:
            # intermittent on haswell bug 89219 fixed in 10c82c6c5fc415d323a5e9c6acdc6a4c85d6b712
            # exclude_tests = exclude_tests + ["arb_uniform_buffer_object.bufferstorage"]
            pass

        if "g965" in o.hardware:
            # intermittent GPU hang on g965
            exclude_tests = exclude_tests + ["arb_shader_texture_lod.execution.tex-miplevel-selection",
                                             # fdo Bug 89398
                                             "glsl-1_20.execution.clipping.fixed-clip-enables",
                                             "glsl-1_10.execution.clipping.clip-plane-transformation pos_clipvert"]

        if "bdw" in o.hardware:
            # many tests match this string and are intermittent on bdw
            exclude_tests = exclude_tests + ["arb_texture_multisample.texelFetch.fs.sampler2dms"]

        if "byt" in o.hardware:
            # bug 89219, fixed in 10c82c6c5fc415d323a5e9c6acdc6a4c85d6b712
            # exclude_tests = exclude_tests + ["arb_uniform_buffer_object.bufferstorage"]
            pass

        for test in exclude_tests:
            fixed_test = test.replace('_', '.')
            fixed_test = fixed_test.replace(' ', '.')
            cmd = cmd + ["--exclude-tests", fixed_test]

        if self.piglit_test:
            include_tests = []
            tests = self.piglit_test.split(",")
            for test in tests:
                # only use the last two components of test name, excluding
                # suffix
                test_name = ".".join(test.split(".")[1:-1])
                # underscores are special in piglit names.  Replace with a '.'
                test_name = test_name.replace('_', '.')
                include_tests = include_tests + ["--include-tests", test_name]
            cmd = cmd + include_tests
            
        cmd = cmd + [self.suite,
                     out_dir ]

        streamedOutput = True
        if self.piglit_test:
            streamedOutput = False
        (out, err) = run_batch_command(cmd, env=env,
                                       expected_return_code=None,
                                       streamedOutput=streamedOutput)
        if err and "There are no tests scheduled to run" in err:
            open(out_dir + "/results.xml", "w").write("<testsuites/>")

        single_out_dir = br + "/../test"
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
                                                         suffix,
                                                         o.arch]) + ".xml")

        # create a copy of the test xml in the source root, where
        # jenkins can access it.
        cmd = ["cp", "-a", "-n",
               br + "/../test", pm.source_root()]
        run_batch_command(cmd)

        Export().export_tests()
        self.check_gpu_hang()

    def filter_tests(self, revisions, infile, outfile):
        t = ET.parse(infile)
        r = t.getroot()
        for a_suite in t.findall("testsuite"):
            # remove skipped tests, which uses ram on jenkins when
            # displaying and provides no value.  
            for a_skip in a_suite.findall("testcase/skipped/.."):
                a_suite.remove(a_skip)

            # for each failure, see if there is an entry in the config
            # file with a revision that was missed by a branch
            for afail in a_suite.findall("testcase/failure/..") + a_suite.findall("testcase/error/.."):
                piglit_test = PiglitTest("foo", "foo", afail)
                regression_revision = piglit_test.GetConfRevision()
                abbreviated_revisions = [a_rev[:6] for a_rev in revisions]
                for abbrev_rev in abbreviated_revisions:
                    if abbrev_rev in regression_revision:
                        a_suite.remove(afail)
                
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
            Jenkins(RevisionSpecification(),
                    Options().result_path).build(reboot_invoke)

    def build(self):
        pass

    def clean(self):
        pass
