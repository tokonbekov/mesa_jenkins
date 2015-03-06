#!/usr/bin/python


import os
import os.path as path
import subprocess
import sys
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

    try:
        bs.build(builder)
    except subprocess.CalledProcessError as e:
        test_path = path.abspath(bs.ProjectMap().build_root() + "/../test/")
        if not path.exists(test_path):
            os.makedirs(test_path)
        # filname has to begin with piglit for junit pattern match in jenkins to find it.
        fh = open(test_path + "/piglitmesa-buildtest_" + global_opts.arch + ".xml", "w")
        fh.write("""\
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="mesa-buildtest" tests="1">
    <testcase classname="compile" name="error" status="fail" time="0">
      <system-out>""" + str(e) + """</system-out>
    </testcase>
  </testsuite>
</testsuites>""")
        bs.Export().export_tests()

if __name__ == '__main__':
    main()
