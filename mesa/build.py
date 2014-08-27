#!/usr/bin/python


import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

options = []
if bs.Options().arch == "m32":
    # gallium requires llvm, which breaks on i386
    # expat pkg-config fails for some reason on i386
    options = ['EXPAT_LIBS="-L/usr/lib/i386-linux-gnu -lexpat"',
               "--with-gallium-drivers=", 
               "--disable-gallium-egl", 
               "--disable-gallium-gbm"]

options = options + [ "--enable-gbm",
                      "--with-egl-platforms=x11,drm" ]
bs.build(bs.AutoBuilder(configure_options = options))

