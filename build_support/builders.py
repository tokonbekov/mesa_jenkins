import os, multiprocessing, re
from . import Options
from . import ProjectMap
from . import run_batch_command
from . import rmtree
from . import Export

class AutoBuilder(object):

    def __init__(self, o=None, configure_options=""):
        self._options = o
        self._configure_options = configure_options
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

        run_batch_command(["../autogen.sh", 
                           "PKG_CONFIG_PATH=" + self._build_root + 
                           "/lib/pkgconfig", 
                           "CC=ccache gcc", "CXX=ccache g++", 
                           "--prefix=" + self._build_root])
        run_batch_command(["make",  "-j", 
                           str(multiprocessing.cpu_count() + 1)])
        run_batch_command(["make",  "install"])

        os.chdir(savedir)

        Export().export()

    def test(self):
        pass

    def clean(self):
        savedir = os.getcwd()
        if not os.path.exists(self._build_dir):
            return
        os.chdir(self._build_dir)
        if os.path.exists("Makefile"):
            run_batch_command(["make", "distclean"])
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

        pkg_config_path = self._project_map.build_root() + \
                          "/lib/pkgconfig:" + \
                          self._project_map.build_root() + \
                          "/lib/x86_64-linux-gnu/pkgconfig"
        run_batch_command(["cmake", self._src_dir, 
                           "-DCMAKE_INSTALL_PREFIX:PATH=" + self._build_root] \
                          + self._extra_definitions,
                          env={"PKG_CONFIG_PATH" : pkg_config_path,
                               "CC":"ccache gcc",
                               "CXX":"ccache g++"})

        run_batch_command(["cmake", "--build", self._build_dir,
                           "--", "-j" + str(multiprocessing.cpu_count() + 1)])
        run_batch_command(["make", "install"])

        os.chdir(savedir)

    def clean(self):
        rmtree(self._build_dir)

    def test(self):
        savedir = os.getcwd()
        os.chdir(self._build_dir)

        # get test names
        command = ["ctest", "-V", "-N"]
        (out, err) = run_batch_command(command, streamedOutput=False, quiet=True)

        os.chdir(savedir)

        out = out.splitlines()
        for aline in out:
            # execute each command reported by ctest
            match = re.match(".*Test command: (.*)", aline)
            if not match:
                continue
            (bin_dir, exe) = os.path.split(match.group(1))
            #bs.GTest(bin_dir, exe, working_dir=bin_dir).run_tests()
    
