import sys, pytest

sys.path.append("..")

import build_support as bs

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
    rs = bs.RepoStatus()
    assert(rs.poll() == [])
    rs._branches[0]._project_branches["mesa"].sha = "bogus"
    assert(rs.poll() == ["mesa_master"])
