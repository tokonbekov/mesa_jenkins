#!/usr/bin/python

import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

repos = bs.RepoSet()
repos.fetch()

rs = bs.RevisionSpecification(from_cmd_line=sys.argv[1:])

rs.checkout()

