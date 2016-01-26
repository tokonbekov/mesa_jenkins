#!/usr/bin/python

import sys
import os.path as path
sys.path.append(path.join(path.dirname(path.abspath(sys.argv[0])), ".."))
import build_support as bs


class MesaBuilder(bs.AutoBuilder):
    def __init__(self):
        global_opts = bs.Options()

        options = []
        if global_opts.arch == "m32":
            # expat pkg-config fails for some reason on i386
            options = ['EXPAT_LIBS="-L/usr/lib/i386-linux-gnu -lexpat"']

        surfaceless = ""
        if path.exists(bs.ProjectMap().project_source_dir() + "/src/egl/drivers/dri2/platform_surfaceless.c"):
            # surfaceless not supported on 10.6 and earlier
            surfaceless = ",surfaceless"

        options = options + ["--enable-gbm",
                             "--with-egl-platforms=x11,drm" + surfaceless,
                             "--enable-glx-tls", 
                             "--enable-gles1",
                             "--enable-gles2",
                             "--with-dri-drivers=i965,swrast,i915",

                             # disable video drivers:
                             # bbe6f7f865cd4316b5f885507ee0b128a20686eb
                             # caused build failure unrelated to intel mesa
                             # team.
                             "--disable-xvmc",
                             "--disable-vdpau",

                             # gallium tested with mesa-buildtest
                             "--without-gallium-drivers"]

        if global_opts.config == 'debug':
            options.append('--enable-debug')

        # always enable optimizations in mesa because tests are too slow
        # without them.
        bs.AutoBuilder.__init__(self, configure_options=options, opt_flags="-O2")
        
        # first post!
        # https://gitlab.khronos.org/vulkan/mesa/issues/1
        self._build_dir = self._src_dir

        gtests = ["src/glx/tests/glx-test",
                  "src/mesa/main/tests/main-test",
                  "src/mesa/drivers/dri/i965/test_vec4_copy_propagation",
                  "src/mesa/drivers/dri/i965/test_vec4_register_coalesce",
                  "./src/mapi/shared-glapi-test"]
        self.AddGtests(gtests)

    def test(self):
        # override the test method, because we can't know exactly
        # where the tests will be as of 11.2
        if path.exists(self._src_dir + "/src/glsl/tests/general-ir-test.cpp"):
            self.AddGtests(["src/glsl/tests/general-ir-test",
                            "src/glsl/tests/sampler-types-test",
                            "src/glsl/tests/uniform-initializer-test"])
        else:
            self.AddGtests(["src/compiler/glsl/tests/general-ir-test",
                            "src/compiler/glsl/tests/sampler-types-test",
                            "src/compiler/glsl/tests/uniform-initializer-test"])

        bs.AutoBuilder.test(self)
       
bs.build(MesaBuilder())
