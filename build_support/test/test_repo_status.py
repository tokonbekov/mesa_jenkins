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

import sys, pytest

sys.path.append("..")

import build_support as bs

def test_dep_graph():
    #pytest.set_trace()
    args= ["ignore_arg0", "--action=build,test", "--config=debug"]
    o = bs.Options(args)
    g = bs.DependencyGraph("all-test", o)
    ready_builds = g.ready_builds()
    assert(ready_builds)
    built = []
    loop_count = 0
    while ready_builds:
        loop_count += 1
        for bi in g.ready_builds():
            assert str(bi) not in built
            built.append(str(bi))
            g.build_complete(bi)
        ready_builds = g.ready_builds()
    assert(loop_count > 2)

def test_project_invoke():
    #pytest.set_trace()
    args= ["ignore_arg0", "--action=build,test", "--config=debug"]
    pi = bs.ProjectInvoke(bs.Options(args), project="mesa")
    pis = str(pi)
    assert(pis == str(bs.ProjectInvoke(from_string=pis)))


def test_repo_checkout():
    #pytest.set_trace()
    build_spec = bs.BuildSpecification()
    build_spec.checkout("mesa_10.2")
    build_spec.checkout("mesa_master")
    

def test_repo_status():
    #pytest.set_trace()
    reposet = bs.RepoSet()
    reposet.fetch()
    rs = bs.RepoStatus()
    assert(rs.poll() == [])
    rs._branches[0]._project_branches["mesa"].sha = "bogus"
    assert(rs.poll() == ["mesa_master"])

def test_revspec():
    #pytest.set_trace()
    rs = bs.RevisionSpecification()
    rs.checkout()

def test_remote():
    #pytest.set_trace()
    spec = bs.BuildSpecification()
    spec.checkout("jekstrand")
    spec.checkout("mesa_master")
