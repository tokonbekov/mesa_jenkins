#!/usr/bin/python

import sys
import os
import os.path as path
import multiprocessing
sys.path.append(path.join(path.dirname(path.abspath(sys.argv[0])), ".."))
import build_support as bs

class SconsBuilder(object):
    def __init__(self):
        self.src_dir = bs.ProjectMap().source_root() + "/repos/mesa"

    def clean(self):
        pass
    
    def test(self):
        pass

    def build(self):
        save_dir = os.getcwd()
        os.chdir(self.src_dir)

        # scons build is broken, will occasionally fail if temporaries
        # are still around.  Use git's nuclear clean method instead of
        # the clean targets.
        bs.run_batch_command(["git", "clean", "-dfx"])

        bs.run_batch_command(["scons", "-j",
                              str(multiprocessing.cpu_count() + 1)])

        bs.run_batch_command(["git", "clean", "-dfx"])
        os.chdir(save_dir)
        
def main():
    b = SconsBuilder()
    bs.build(b)


if __name__ == '__main__':
    main()
