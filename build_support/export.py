"""handles synchronization of the build_root with the results directory"""
import os
import subprocess
from . import run_batch_command
from . import rmtree
from . import Options
from . import ProjectMap

class Export:
    def __init__(self):
        # todo: provide wildcard mechanism
        self.result_path = Options().result_path
        if not self.result_path:
            return

        if not os.path.exists(self.result_path):
            os.makedirs(self.result_path)

    def export(self):
        if not os.path.exists(self.result_path):
            os.makedirs(self.result_path)

        cmd = ["rsync", "-rlptD",
               ProjectMap().build_root(), self.result_path]

        try:
            run_batch_command(cmd)
        except subprocess.CalledProcessError as e:
            print "WARN: some errors copying: " + str(e)

        self.export_tests()

    def export_tests(self):

        test_path = os.path.abspath(ProjectMap().build_root() + "/../test")
        if not os.path.exists(test_path):
            os.makedirs(test_path)

        cmd = ["rsync", "-rlptD",
               test_path, 
               self.result_path]

        try:
            run_batch_command(cmd)
        except subprocess.CalledProcessError as e:
            print "WARN: some errors copying: " + str(e)
        

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

        cmd = ["rsync", "-rlptD", 
               result_path, br]

        # don't want to confuse test results with any preexisting
        # files in the build root.
        test_dir = os.path.normpath(br + "/../test")
        if os.path.exists(test_dir):
            rmtree(test_dir)

        try:
            run_batch_command(cmd)
        except subprocess.CalledProcessError as e:
            print "WARN: some errors copying: " + str(e)
