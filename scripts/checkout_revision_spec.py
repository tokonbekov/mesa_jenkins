#!/usr/bin/python

import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

revs = []
for rev in sys.argv[1:]:
    rev = rev.split("=")
    rev[1] = '"' + rev[1] + '"'
    revs.append(rev[0] + "=" + rev[1])
rev_text = "<RevSpec " + " ".join(revs) + "/>"
rs = bs.RevisionSpecification(rev_text)

rs.checkout()

