#!/usr/bin/python

import sys
import os
import time
import stat
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs


# from http://stackoverflow.com/questions/6879364/print-file-age-in-seconds-using-python
def file_age_in_seconds(pathname):
    return time.time() - os.stat(pathname)[stat.ST_MTIME]

def file_age_in_days(pathname):
    return file_age_in_seconds(pathname) / (60*60*24)

result_path = "/mnt/jenkins/results/"

for a_dir in os.listdir(result_path):
    sub_dir = result_path + a_dir
    for a_build_dir in os.listdir(sub_dir):
        build_dir = sub_dir + "/" + a_build_dir
        if os.path.islink(build_dir):
            continue
        if file_age_in_days(build_dir) > 30:
            bs.rmtree(build_dir)
