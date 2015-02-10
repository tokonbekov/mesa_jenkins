#!/usr/bin/python

import xml.etree.ElementTree as ET
import ConfigParser as CP
import sys, os, glob
import argparse

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
parser.add_argument('junit_file', metavar='junit_file', type=str, nargs='+',
                    help='test files to use for update')
args = parser.parse_args(sys.argv[1:])

xmls = []
for junit in args.junit_file:
    xmls = xmls + glob.glob(junit)


for f in xmls:
    print "parsing " + f
    t = ET.parse(f)
    r = t.getroot()

    fn = os.path.splitext(os.path.split(f)[-1])[0]
    hw = fn.split("_")[1]
    if "gt" in hw:
        hw = hw[:3]

    arch = fn.split("_")[2]
    conf_file = script_dir + hw + arch + ".conf"
    if not os.path.exists(conf_file):
        conf_file = script_dir + hw + ".conf"
        assert(os.path.exists(conf_file))
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
        if failnode.attrib["type"] == "fail":
            c.set("expected-failures", name)
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
        c.set("expected-crashes", name)

    c.write(open(conf_file, "w"))
