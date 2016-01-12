#!/usr/bin/python

import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

arch = bs.Options().arch

# mostly this is necessary because cts has no make install
class CtsBuilder(bs.CMakeBuilder):
    def __init__(self):
        bs.CMakeBuilder.__init__(self,
                                 extra_definitions=["-DDEQP_TARGET=intel-gbm",
                                                    "-DCMAKE_INCLUDE_PATH=/tmp/build_root/usr/include",
                                                    "-DCMAKE_LIBRARY_PATH=/tmp/build_root/" + arch + "/lib"])
    def build(self):
        pm = bs.ProjectMap()
        if not os.path.exists(self._build_dir):
            os.makedirs(self._build_dir)

        savedir = os.getcwd()
        os.chdir(self._build_dir)

        cflag = "-m32"
        cxxflag = "-m32"
        if self._options.arch == "m64":
            cflag = "-m64"
            cxxflag = "-m64"
        env = {"CC":"ccache gcc",
               "CXX":"ccache g++",
               "CFLAGS":cflag,
               "CXXFLAGS":cxxflag}
        self._options.update_env(env)
        
        bs.run_batch_command(["cmake", "-GNinja", self._src_dir] + self._extra_definitions,
                             env=env)

        bs.run_batch_command(["ninja","-j" + str(bs.cpu_count())], env=env)

        bs.run_batch_command(["mkdir", "-p", pm.build_root() + "/bin"])
        bs.run_batch_command(["cp", "-a", self._build_dir + "/cts",
                              pm.build_root() + "/bin"])

        os.chdir(savedir)

        bs.Export().export()
        
bs.build(CtsBuilder())
