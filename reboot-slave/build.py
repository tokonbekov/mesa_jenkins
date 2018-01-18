#!/usr/bin/python

import os
import sys
import urllib2
import ast
import time
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "..", "repos", "mesa_ci"))
import build_support as bs
server = bs.ProjectMap().build_spec().find("build_master").attrib["host"]

url = "http://" + server + "/computer/api/python"
f=urllib2.urlopen(url)
host_dict = ast.literal_eval(f.read())

def is_excluded():
    if ("builder" in host or host == "master"):
        return True

for a_host in host_dict['computer']:
    host = a_host['displayName']
    if is_excluded():
        continue
    url = "http://" + server + "/job/reboot_single/buildWithParameters?token=noauth&label=" + host
    urllib2.urlopen(url)
    time.sleep(10)
