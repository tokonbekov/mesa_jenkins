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
            return 120
        return 30

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

bs.build(bs.PerfBuilder("synmark_long", high_variance_benchmarks, iterations=2),
         time_limit=SynmarkTimeout())

