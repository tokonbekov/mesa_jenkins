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

high_variance_benchmarks = ["OglFillTexSingle",
                            "OglBatch3",
                            "OglDeferred",
                            "OglBatch1",
                            "OglBatch4",
                            "OglGeomPoint",
                            "OglBatch0",
                            "OglHdrBloom",
                            "OglCSCloth",
                            "OglShMapVsm",
                            "OglVSTangent",
                            "OglFillTexMulti",
                            "OglFillPixel",
                            "OglGeomTriList"]

bs.build(bs.PerfBuilder("synmark_long", high_variance_benchmarks, iterations=2),
         time_limit=SynmarkTimeout())
