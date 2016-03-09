#!/usr/bin/python

import bz2
import os
import re
import sys
import xml.etree.ElementTree  as ET

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs


class SlowTimeout:
    def __init__(self):
        self.hardware = bs.Options().hardware

    def GetDuration(self):
        return 500

bs.build(bs.DeqpBuilder(), time_limit=SlowTimeout())
        
