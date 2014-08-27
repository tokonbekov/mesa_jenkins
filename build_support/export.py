"""handles synchronization of the build_root with the results directory"""
import os
from . import run_batch_command
from . import rmtree
from . import Options
from . import ProjectMap

class Export:
    def __init__(self):
        # todo: provide wildcard mechanism
        pass

    def export(self):
        result_path = Options().result_path
        if not result_path:
            return

        if not os.path.exists(result_path):
            os.makedirs(result_path)

        cmd = ["cp", "-a", "-n",
               ProjectMap().build_root(), result_path]

        test_path = os.path.abspath(ProjectMap().build_root() + "/../test")
        if not os.path.exists(test_path):
            os.makedirs(test_path)

        cmd = ["cp", "-a", "-n",
               test_path, 
               result_path]

        run_batch_command(cmd)

    def import_build_root(self):
        o = Options()
        result_path = o.result_path + "/" + o.arch
        if not result_path:
            return
        if not os.path.exists(result_path):
            return

        br = os.path.dirname(ProjectMap().build_root())
        if not os.path.exists(br):
            os.makedirs(br)

        cmd = ["cp", "-a", "-n",
               result_path, br]

        # don't want to confuse test results with any preexisting
        # files in the build root.
        test_dir = os.path.normpath(br + "/../test")
        if os.path.exists(test_dir):
            rmtree(test_dir)

        run_batch_command(cmd)
