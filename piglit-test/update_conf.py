#!/usr/bin/python

import ConfigParser as CP
import argparse
from email.mime.text import MIMEText
import git
import glob
import os
import smtplib
import sys
import xml.etree.ElementTree as ET

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

# needed to preserve case in the options
class CaseConfig(CP.SafeConfigParser):
    def optionxform(self, optionstr):
        return optionstr

script_dir = os.path.dirname(sys.argv[0])
if not script_dir:
    script_dir = "."
script_dir = script_dir + "/"
    
parser = argparse.ArgumentParser(description="updates expected failures")

parser.add_argument('--blame_revision', type=str, required=True,
                    help='revision to specify as the cause of any config changes')
parser.add_argument('--result_path', metavar='result_path', type=str, default="",
                    help='path to build results')
parser.add_argument('--to', metavar='to', type=str, default="",
                    help='send resulting patch to this email')
parser.add_argument('junit_file', metavar='junit_file', type=str, nargs='*',
                    help='test files to use for update')
args = parser.parse_args(sys.argv[1:])

xmls = []
for junit in args.junit_file:
    xmls = xmls + glob.glob(junit)

if args.result_path and os.path.exists(args.result_path):
    test_dir = args.result_path + "/test"
    for a_file in os.listdir(test_dir):
        if "piglit-" in a_file:
            xmls = xmls + [test_dir + "/" + a_file]

for f in xmls:
    print "parsing " + f
    t = ET.parse(f)
    r = t.getroot()

    fn = os.path.splitext(os.path.split(f)[-1])[0]
    hw = fn.split("_")[-2]

    build_name = fn.split("_")[0]
    nir = True
    if "nir" in build_name:
        nir = False

    arch = fn.split("_")[-1]
    
    conf_file = bs.get_conf_file(hw, arch, nir)
            
    print "updating " + conf_file
    c = CaseConfig(allow_no_value=True)
    c.optionxform = str
    c.read(conf_file)
    
    for afail in r.findall(".//failure/.."):
        
        # strip the arch/hw off the end of the name
        name = ".".join(afail.attrib["name"].split(".")[:-1])
        name = afail.attrib["classname"] + "." + name
        name = name.replace("=", ".")
        name = name.replace(":", ".")

        failnode = afail.find("./failure")
        if failnode.attrib["type"] == "fail" or failnode.attrib["type"] == "warn":
            c.set("expected-failures", name, args.blame_revision)
            continue
        assert(failnode.attrib["type"] == "pass")
        c.remove_option("expected-failures", name)
        c.remove_option("expected-crashes", name)
        if not c.has_section("fixed-tests"):
            c.add_section("fixed-tests")
        c.set("fixed-tests", name, args.blame_revision)
    for acrash in r.findall(".//error/.."):
        # strip the arch/hw off the end of the name
        name = ".".join(acrash.attrib["name"].split(".")[:-1])
        name = acrash.attrib["classname"] + "." + name
        name = name.replace("=", ".")
        name = name.replace(":", ".")
        c.set("expected-crashes", name, args.blame_revision)

    c.write(open(conf_file, "w"))

if args.to:
    patch_text = git.Repo().git.diff()
    msg = MIMEText(patch_text)
    msg["Subject"] = "[PATCH] mesa jenkins updates due to " + args.blame_revision
    msg["From"] = "Do Not Reply <mesa_jenkins@intel.com>"
    msg["To"] = args.to
    s = smtplib.SMTP('or-out.intel.com')
    to = args.to.split(",")
    s.sendmail(msg["From"], to, msg.as_string())
