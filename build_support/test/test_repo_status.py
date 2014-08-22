import sys, pytest

sys.path.append("..")

import build_support as bs

def test_dep_graph():
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
