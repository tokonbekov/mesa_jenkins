#!/usr/bin/python

import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

class AutoBuilder(object):

    def __init__(self, o=None):
        self._options = o
        if not o:
            self._options = bs.Options()
        self._src_dir = os.path.abspath(os.path.dirname(os.path.abspath(sys.argv[0])) + "/../../mesa")
        self._build_dir = self._src_dir + "/build"

    def build(self):
        if not os.path.exists(self._build_dir):
            os.makedirs(self._build_dir)
        savedir = os.getcwd()
        os.chdir(self._src_dir)

        bs.run_batch_command(["./autogen.sh"])
        bs.run_batch_command(["make",  "-j"])

        os.chdir(savedir)

    def test(self):
        pass

    def clean(self):
        savedir = os.getcwd()
        os.chdir(self._src_dir)
        bs.run_batch_command(["make clean"])
        os.chdir(savedir)

bs.build(AutoBuilder())

