#!/usr/bin/python


import sys
import os.path as path
sys.path.append(path.join(path.dirname(path.abspath(sys.argv[0])), ".."))
import build_support as bs


def main():
    global_opts = bs.Options()

    options = []
    if global_opts.arch == "m32":
        # gallium requires llvm, which breaks on i386
        # expat pkg-config fails for some reason on i386
        options = ['EXPAT_LIBS="-L/usr/lib/i386-linux-gnu -lexpat"']

    options = options + ["--enable-gbm",
                         "--with-egl-platforms=x11,drm",
                         "--enable-glx-tls", 
                         "--enable-gles1",
                         "--enable-gles2",
                         "--with-gallium-drivers=i915,svga,swrast,r300,r600,radeonsi,nouveau"]

    if global_opts.config == 'debug':
        options.append('--enable-debug')

    builder = bs.AutoBuilder(configure_options=options, export=False)

    bs.build(builder)


if __name__ == '__main__':
    main()
