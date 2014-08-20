import sys, pytest

sys.path.append("..")

import build_support as bs

def test_repo_status():
    #pytest.set_trace()
    rs = bs.RepoStatus("test_spec.xml")
    assert(rs.poll() == [])
    rs._branches[0]._project_branches["fips"].sha = "bogus"
    assert(rs.poll() == ["fips_master"])
    

def test_repo_checkout():
    #pytest.set_trace()
    build_spec = bs.BuildSpecification("test_spec.xml")
    build_spec.checkout("reset_metrics")
    build_spec.checkout("fips_master")
    
