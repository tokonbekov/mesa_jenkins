import os, multiprocessing
from . import Options
from . import ProjectMap
from . import run_batch_command
from . import rmtree


class AutoBuilder(object):

    def __init__(self, o=None):
        self._options = o
        if not o:
            self._options = Options()
            
        self._project_map = ProjectMap()
        project = self._project_map.current_project()

        self._src_dir = self._project_map.project_source_dir(project)
        self._build_root = self._project_map.build_root()

    def build(self):
        if not os.path.exists(self._build_root):
            os.makedirs(self._build_root)
        savedir = os.getcwd()
        os.chdir(self._src_dir)

        run_batch_command(["./autogen.sh", "PKG_CONFIG_PATH=" + self._build_root + "lib/pkgconfig", 
                           "CC=ccache gcc", "CXX=ccache g++", 
                              "--prefix=" + self._build_root])
        run_batch_command(["make",  "-j", str(multiprocessing.cpu_count() + 1)])
        run_batch_command(["make",  "install"])

        os.chdir(savedir)

    def test(self):
        pass

    def clean(self):
        savedir = os.getcwd()
        os.chdir(self._src_dir)
        run_batch_command(["make", "distclean"])
        os.chdir(savedir)
