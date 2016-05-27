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

low_variance_benchmarks = ["OglPSBump8",
                           "OglDeferredAA",
                           "OglTexMem128",
                           "OglTerrainPanTess",
                           "OglPSPhong",
                           "OglVSDiffuse1",
                           "OglPSPom",
                           "OglGeomTriStrip",
                           "OglPSBump2",
                           "OglTexMem512",
                           "OglTexFilterAniso",
                           "OglVSDiffuse8",
                           "OglTexFilterTri",
                           "OglShMapPcf"]

bs.build(bs.PerfBuilder("synmark_long", low_variance_benchmarks, iterations=3),
         time_limit=SynmarkTimeout())

