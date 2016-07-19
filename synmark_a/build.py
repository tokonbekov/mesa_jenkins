#!/usr/bin/python

import sys
import os.path as path
sys.path.append(path.join(path.dirname(path.abspath(sys.argv[0])), ".."))
import build_support as bs

class SynmarkTimeout:
    def __init__(self):
        self._options = bs.Options()
    def GetDuration(self):
        if self._options.type == "daily":
            return 240
        return 30

def iterations(bench, hw):
    if bench == "OglBatch5":
        if hw == "skl":
            return 4
    if bench == "OglBatch6":
        if hw == "bdw":
            return 7
        return 4
    if bench == "OglBatch7":
        return 4
    if bench == "OglDrvRes":
        if hw == "skl":
            return 3
    if bench == "OglDrvState":
        return 4
    if bench == "OglTerrainFlyInst":
        if hw == "skl":
            return 3
    if bench == "OglZBuffer":
        if hw == "bdw":
            return 3
    if bench == "OglTerrainFlyTess":
        if hw == "bdw":
            return 4
    
    
high_variance_benchmarks = ["OglVSInstancing",
                            "OglTerrainFlyInst",
                            "OglMultithread",
                            "OglBatch7",
                            "OglDrvRes",
                            "OglDrvShComp",
                            "OglCSDof",
                            "OglBatch6",
                            "OglTerrainFlyTess",
                            "OglDrvState",
                            "OglBatch5",
                            "OglTerrainPanInst",
                            "OglZBuffer",
                            "OglBatch2"]

bs.build(bs.PerfBuilder("synmark_long", high_variance_benchmarks, iterations=2,
                        custom_iterations_fn=iterations),
         time_limit=SynmarkTimeout())

