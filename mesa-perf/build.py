 #!/usr/bin/python

import os
import sys
import os.path as path
sys.path.append(path.join(path.dirname(path.abspath(sys.argv[0])), ".."))
import build_support as bs


class MesaPerf:
    def __init__(self):
        opts = bs.Options()

        if opts.arch == "m32":
            # only run perf tests on m64
            print "ERROR: perf not supported for i386"
            assert(False)
        if opts.config == 'debug':
            print "ERROR: perf not supported for debug"
            assert(False)

        pm = bs.ProjectMap()
        self._src_dir = pm.project_source_dir("mesa")
        self._build_dir = "/tmp/build_root/perf/build/"


        self._flags = {
            "skl" : ["-march=broadwell", "-mmmx", "-mno-3dnow",
                     "-msse", "-msse2", "-msse3", "-mssse3",
                     "-mno-sse4a", "-mcx16", "-msahf", "-mmovbe",
                     "-maes", "-mno-sha", "-mpclmul", "-mpopcnt",
                     "-mabm", "-mno-lwp", "-mfma", "-mno-fma4",
                     "-mno-xop", "-mbmi", "-mbmi2", "-mno-tbm",
                     "-mavx", "-mavx2", "-msse4.2", "-msse4.1",
                     "-mlzcnt", "-mrtm", "-mhle", "-mrdrnd", "-mf16c",
                     "-mfsgsbase", "-mrdseed", "-mprfchw", "-madx",
                     "-mfxsr", "-mxsave", "-mxsaveopt",
                     "-mno-avx512f", "-mno-avx512er", "-mno-avx512cd",
                     "-mno-avx512pf", "-mno-prefetchwt1",
                     "-mclflushopt", "-mxsavec", "-mxsaves",
                     "-mno-avx512dq", "-mno-avx512bw",
                     "-mno-avx512vl", "-mno-avx512ifma",
                     "-mno-avx512vbmi", "-mno-clwb", "-mno-pcommit",
                     "-mno-mwaitx", "--param", "l1-cache-size=32",
                     "--param", "l1-cache-line-size=64", "--param",
                     "l2-cache-size=4096", "-mtune=generic"],
            "bdw" : ["-march=broadwell", "-mmmx", "-mno-3dnow",
                     "-msse", "-msse2", "-msse3", "-mssse3",
                     "-mno-sse4a", "-mcx16", "-msahf", "-mmovbe",
                     "-maes", "-mno-sha", "-mpclmul", "-mpopcnt",
                     "-mabm", "-mno-lwp", "-mfma", "-mno-fma4",
                     "-mno-xop", "-mbmi", "-mbmi2", "-mno-tbm",
                     "-mavx", "-mavx2", "-msse4.2", "-msse4.1",
                     "-mlzcnt", "-mrtm", "-mhle", "-mrdrnd", "-mf16c",
                     "-mfsgsbase", "-mrdseed", "-mprfchw", "-madx",
                     "-mfxsr", "-mxsave", "-mxsaveopt",
                     "-mno-avx512f", "-mno-avx512er", "-mno-avx512cd",
                     "-mno-avx512pf", "-mno-prefetchwt1", "--param",
                     "l1-cache-size=32", "--param",
                     "l1-cache-line-size=64", "--param",
                     "l2-cache-size=6144", "-mtune=generic"]
            }
        
    def build(self):
        options = ["--enable-glx-tls", 
                   "--enable-gles1",
                   "--enable-gles2",
                   "--with-dri-drivers=i965,i915",

                   # disable video drivers:
                   # bbe6f7f865cd4316b5f885507ee0b128a20686eb
                   # caused build failure unrelated to intel mesa
                   # team.
                   "--disable-xvmc",
                   "--disable-vdpau",

                   # gallium tested with mesa-buildtest
                   "--without-gallium-drivers"]

        save_dir = os.getcwd()
        for hw in ["skl", "bdw"]:
            bd = self._build_dir + hw
            if not os.path.exists(bd):
                os.makedirs(bd)
            os.chdir(bd)
            
            flags = " ".join(self._flags[hw])
            flags = ["CFLAGS=-O2 " + flags,
                     "CXXFLAGS=-O2 " + flags,
                     "CC=ccache gcc",
                     "CXX=ccache g++"]
            cmd = [self._src_dir + "/autogen.sh"] + flags + options
            bs.run_batch_command(cmd)
            bs.run_batch_command(["make", "-j", str(bs.cpu_count()),
                                  "install"],
                                 env={"DESTDIR" : "/tmp/build_root/perf/" + hw} )
        os.chdir(save_dir)

    def clean(self):
        pm = bs.ProjectMap()
        bs.git_clean(pm.project_source_dir("mesa"))
        bs.rmtree(self._build_dir)

    def test(self):
        pass
       
bs.build(MesaPerf())
