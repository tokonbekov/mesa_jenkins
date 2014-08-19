import sys, pytest

sys.path.append("..")

import build_support as bs

def test_repo_status():
    #pytest.set_trace()
    rs = bs.RepoStatus("test_spec.xml")
    assert(rs.poll() == [])
    rs._branches[0]._project_branches["fips"].sha = "bogus"
    assert(rs.poll() == ["fips_master"])
    
