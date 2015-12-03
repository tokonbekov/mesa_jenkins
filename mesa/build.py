#!/usr/bin/python

import sys
import os.path as path
sys.path.append(path.join(path.dirname(path.abspath(sys.argv[0])), ".."))
import build_support as bs


def main():
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
    builder = bs.AutoBuilder(configure_options=options, opt_flags="-O2")

    # first post!
    # https://gitlab.khronos.org/vulkan/mesa/issues/1
    builder._build_dir = builder._src_dir

    gtests = ["src/glsl/tests/general-ir-test",
              "src/glsl/tests/sampler-types-test",
              "src/glsl/tests/uniform-initializer-test",
              "src/glx/tests/glx-test",
              "src/mesa/main/tests/main-test",
              "src/mesa/drivers/dri/i965/test_vec4_copy_propagation",
              "src/mesa/drivers/dri/i965/test_vec4_register_coalesce",
              "./src/mapi/shared-glapi-test"]

    builder.AddGtests(gtests)

    bs.build(builder)


if __name__ == '__main__':
    main()
