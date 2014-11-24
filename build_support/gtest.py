"""Handles running of gtest executables"""
import os
import sys
import subprocess

from . import Options
from . import ProjectMap
from . import rmfile
from . import run_batch_command

class GTest:
    """Runs google test executables, publishing results to server"""
    def __init__(self, binary_dir, executables):
        """explanation of parameters:
            binary_dir:  directory containing the executables.
            executables: list of gtest executables
        """
        self._bin_dir = binary_dir
        self._executables = executables
        if type(executables) != type([]):
            self._executables = [executables]

    def run_tests(self):
        """
        nonzero return is an error
        """
        
        options = Options()

        pm = ProjectMap()
        br = pm.build_root()
        for test in self._executables:
            outname = "_".join(["gtest", 
                                os.path.basename(test),
                                options.config, 
                                options.arch,
                                options.hardware,
                            ]) + ".xml"
            outpath = br + "/../test/" + outname
            if os.path.exists(outpath):
                rmfile(outpath)

            test_path = os.path.join(self._bin_dir, test)
            cmd = [test_path,
                   "--gtest_output=xml:" + outpath,
                   "--gtest_catch_exceptions"]
            try:
                run_batch_command(cmd)
            except(subprocess.CalledProcessError):
                print "WARN: gtest returned non-zero status"
            
            if not os.path.exists(outpath):
                print "ERROR: gtest produced no output: " + test_path
                sys.exit(-1)

        # create a copy of the test xml in the source root, where
        # jenkins can access it.
        cmd = ["cp", "-a", "-n",
               br + "/../test", pm.source_root()]
        run_batch_command(cmd)
