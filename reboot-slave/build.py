#!/usr/bin/python

import sys, os, argparse
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

import time

# add a sleep so the scheduler can dispatch all the jobs before the first one fails
time.sleep(30)

bs.run_batch_command(["sudo", "reboot"])
