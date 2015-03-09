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

    pm = bs.ProjectMap()
    try:
        bs.build(builder)
    except subprocess.CalledProcessError as e:
        test_path = path.abspath(pm.build_root() + "/../test/")
        if not path.exists(test_path):
            os.makedirs(test_path)
        # filname has to begin with piglit for junit pattern match in jenkins to find it.
        fh = open(test_path + "/piglitmesa-buildtest_" + global_opts.arch + ".xml", "w")
        fh.write("""\
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="mesa-buildtest" tests="1">
    <testcase classname="mesa-buildtest-""" + global_opts.arch + """\
" name="compile.error" status="fail" time="0">
      <system-out>""" + xml.sax.saxutils.escape(str(e)) + """</system-out>
      <failure type="fail" />
    </testcase>
  </testsuite>
</testsuites>""")
        fh.close()
        bs.Export().export_tests()

        # create a copy of the test xml in the source root, where
        # jenkins can access it.
        cmd = ["cp", "-a", "-n",
               pm.build_root() + "/../test", pm.source_root()]
        bs.run_batch_command(cmd)

if __name__ == '__main__':
    main()
