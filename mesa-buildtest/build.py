#!/usr/bin/python


import os
import os.path as path
import subprocess
import sys
import xml.sax.saxutils
sys.path.append(path.join(path.dirname(path.abspath(sys.argv[0])), ".."))
import build_support as bs


def main():
    global_opts = bs.Options()

    options = []
    if global_opts.arch == "m32":
        # m32 build not supported
        return

    options = options + ["--enable-gbm",
                         "--with-egl-platforms=x11,drm",
                         "--enable-glx-tls", 
                         "--enable-gles1",
                         "--enable-gles2",
                         "--with-gallium-drivers=i915,svga,swrast,r300,r600,radeonsi,nouveau"]

    if global_opts.config == 'debug':
        options.append('--enable-debug')

    builder = bs.AutoBuilder(configure_options=options, export=False)

    try:
        bs.build(builder)
    except subprocess.CalledProcessError as e:
        bs.Export().create_failing_test("mesa-buildtest", str(e))

if __name__ == '__main__':
    main()
