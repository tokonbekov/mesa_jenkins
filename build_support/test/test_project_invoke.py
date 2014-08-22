import sys, pytest, tempfile, shutil

sys.path.append("..")

import build_support as bs

def test_build_info():
    t = tempfile.mkdtemp()
    args= ["ignore_arg0", "--result_path", t]
    o = bs.Options(args)
    pi = bs.ProjectInvoke(o, project="mesa")
    pi.set_info("status", "done")
    assert(pi.get_info("status") == "done")
    shutil.rmtree(t)

