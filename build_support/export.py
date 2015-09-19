# Copyright (C) Intel Corp.  2014.  All Rights Reserved.

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice (including the
# next paragraph) shall be included in all copies or substantial
# portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE COPYRIGHT OWNER(S) AND/OR ITS SUPPLIERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#  **********************************************************************/
#  * Authors:
#  *   Mark Janes <mark.a.janes@intel.com>
#  **********************************************************************/

"""handles synchronization of the build_root with the results directory"""
import os
import random
import socket
import subprocess
import time
import xml.sax.saxutils
from . import run_batch_command
from . import rmtree
from . import Options
from . import ProjectMap

class Export:
    def __init__(self):
        # todo: provide wildcard mechanism
        self.result_path = Options().result_path
        if not self.result_path:
            return

        if not os.path.exists(self.result_path):
            os.makedirs(self.result_path)

    def export(self):
        if not self.result_path:
            return
        if not os.path.exists(self.result_path):
            os.makedirs(self.result_path)

        cmd = ["rsync", "-rlptD",
               ProjectMap().build_root(), self.result_path]

        try:
            run_batch_command(cmd)
        except subprocess.CalledProcessError as e:
            print "WARN: some errors copying: " + str(e)

        self.export_tests()

    def export_tests(self):
        if not self.result_path:
            return

        test_path = os.path.abspath(ProjectMap().build_root() + "/../test")
        if not os.path.exists(test_path):
            os.makedirs(test_path)

        cmd = ["rsync", "-rlptD",
               test_path, 
               self.result_path]

        try:
            run_batch_command(cmd)
            run_batch_command(["sync"])
        except subprocess.CalledProcessError as e:
            print "WARN: some errors copying: " + str(e)
        

    def import_build_root(self):
        o = Options()
        result_path = o.result_path + "/" + o.arch
        if not o.result_path:
            return
        if not os.path.exists(result_path):
            print "WARN: no build root to import, sleeping"
            time.sleep(10)
        if not os.path.exists(result_path):
            print "WARN: no build root to import: " + result_path
            return

        br = os.path.dirname(ProjectMap().build_root())
        if not os.path.exists(br):
            os.makedirs(br)

        cmd = ["rsync", "-rlptD", 
               result_path, br]

        # don't want to confuse test results with any preexisting
        # files in the build root.
        test_dir = os.path.normpath(br + "/../test")
        if os.path.exists(test_dir):
            rmtree(test_dir)

        try:
            run_batch_command(cmd)
        except subprocess.CalledProcessError as e:
            print "WARN: some errors copying: " + str(e)

    def create_failing_test(self, failure_name, output):
        o = Options()
        pm = ProjectMap()
        test_path = os.path.abspath(pm.build_root() + "/../test/")
        print "ERROR: creating a failing test: " + failure_name + " : " + output
        if not os.path.exists(test_path):
            os.makedirs(test_path)

        randstr = socket.gethostname() + "_" + str(random.random())[2:6]
        # filname has to begin with piglit for junit pattern match in jenkins to find it.
        fh = open(test_path + "/piglit-fail-" + o.hardware + o.arch + "_" + randstr + ".xml", "w")
        failure_name = failure_name + "-" + o.hardware + o.arch
        fh.write("""\
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="generated-failures" tests="1">
    <testcase classname="failure-""" + failure_name + """\
" name="compile.error" status="fail" time="0">
      <system-out>""" + xml.sax.saxutils.escape(output) + """</system-out>
      <failure type="fail" />
    </testcase>
  </testsuite>
</testsuites>""")
        fh.close()
        Export().export_tests()

        # create a copy of the test xml in the source root, where
        # jenkins can access it.
        cmd = ["cp", "-a", "-n",
               pm.build_root() + "/../test", pm.source_root()]
        run_batch_command(cmd)
        
