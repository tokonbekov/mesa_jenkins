#!/usr/bin/python


import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "..", "repos", "mesa_ci"))
import build_support as bs

bs.build(bs.CMakeBuilder(extra_definitions=["-Dwaffle_has_x11_egl=1", 
                                            "-Dwaffle_has_glx=1",
                                            "-Dwaffle_has_gbm=1",
                                            "-Dwaffle_has_wayland=0",
                                        ] ))
