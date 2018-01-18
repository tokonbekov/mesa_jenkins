#!/usr/bin/python


import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "..", "repos", "mesa_ci"))
import build_support as bs

opts = [
    '-DPIGLIT_BUILD_DMA_BUF_TESTS=1',
    '-DPIGLIT_BUILD_GLES1_TESTS=1',
    '-DPIGLIT_BUILD_GLES2_TESTS=1',
    '-DPIGLIT_BUILD_GLES3_TESTS=1',
    '-DPIGLIT_BUILD_GL_TESTS=1',
    '-DPIGLIT_BUILD_GLX_TESTS=1',
    '-DPIGLIT_BUILD_CL_TESTS=0',
]

builder = bs.CMakeBuilder(extra_definitions=opts)

bs.build(builder)
