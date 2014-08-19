#!/usr/bin/python


import sys, os, multiprocessing
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

class AutoBuilder(object):

    def __init__(self, o=None):
        self._options = o
        if not o:
            self._options = bs.Options()
            
        self._project_map = bs.ProjectMap()
        project = self._project_map.current_project()

        self._src_dir = self._project_map.project_source_dir(project)
        self._build_root = self._project_map.build_root()

    def build(self):
        if not os.path.exists(self._build_root):
            os.makedirs(self._build_root)
        savedir = os.getcwd()
        os.chdir(self._src_dir)

        bs.run_batch_command(["./autogen.sh", "CC=ccache gcc", "CXX=ccache g++", 
                              "--prefix=" + self._build_root])
        bs.run_batch_command(["make",  "-j", str(multiprocessing.cpu_count() + 1)])
        bs.run_batch_command(["make",  "install"])

        os.chdir(savedir)

    def test(self):
        pass

    def clean(self):
        savedir = os.getcwd()
        os.chdir(self._src_dir)
        bs.run_batch_command(["make", "clean"])
        bs.rmtree(self._build_root)
        os.chdir(savedir)

bs.build(AutoBuilder())

