#!/usr/bin/python

import os
import sys
import os.path as path
sys.path.append(path.join(path.dirname(path.abspath(sys.argv[0])), "..", "repos", "mesa_ci"))
import build_support as bs


def iterations(_, hw):
    if hw == "bdw":
        return 7

bs.build(bs.PerfBuilder("fill_o", iterations=5,
                        custom_iterations_fn=iterations))

