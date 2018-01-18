#!/usr/bin/python


import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "..", "repos", "mesa_ci"))
import build_support as bs

class DrmBuilder(bs.AutoBuilder):
    def __init__(self):
        bs.AutoBuilder.__init__(
            self,
            configure_options=[
                '--enable-etnaviv-experimental-api',
                '--enable-freedreno',
            ],
        )

    def test(self):
        # libdrm now has a 2-minute long test, which is too long to
        # wait for.
        pass

bs.build(DrmBuilder())

