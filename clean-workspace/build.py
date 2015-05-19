#!/usr/bin/python

import sys, os, argparse
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

bs.run_batch_command(["git", "clean", "-xfd"])
bs.run_batch_command(["git", "reset", "--hard", "HEAD"])
bs.rmtree("repos")
