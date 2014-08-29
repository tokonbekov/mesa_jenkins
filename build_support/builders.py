import os, multiprocessing, re, subprocess
from . import Options
from . import ProjectMap
from . import run_batch_command
from . import rmtree
from . import Export
from . import GTest

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

class AutoBuilder(object):

    def __init__(self, o=None, configure_options=None):
        self._options = o
        self._tests = None

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

        savedir = os.getcwd()
        os.chdir(self._build_dir)
        flags = []
        if self._options.arch == "m32":
            flags = ["CFLAGS=-m32", "CXXFLAGS=-m32", 
                     "--enable-32-bit",
                     "--host=i686-pc-linux-gnu"]
        else:
            flags = ["CFLAGS=-m64", "CXXFLAGS=-m64"]

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
        rmtree(self._build_dir)


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
        rmtree(self._build_dir)

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
    
