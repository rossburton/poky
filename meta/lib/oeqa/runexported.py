#!/usr/bin/env python


# Copyright (C) 2013 Intel Corporation
#
# Released under the MIT license (see COPYING.MIT)

# This script should be used outside of the build system to run image tests.
# It needs a json file as input as exported by the build.
# E.g for an already built image:
#- export the tests:
#   TEST_EXPORT_ONLY = "1"
#   TEST_TARGET  = "simpleremote"
#   TEST_TARGET_IP = "192.168.7.2"
#   TEST_SERVER_IP = "192.168.7.1"
# bitbake core-image-sato -c testimage
# Setup your target, e.g for qemu: runqemu core-image-sato
# cd build/tmp/testimage/core-image-sato
# ./runexported.py testdata.json

import sys
import os
import time
import argparse
import re

from oeqa.utils.testsexport import get_dest_folder

try:
    import simplejson as json
except ImportError:
    import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "oeqa")))

from oeqa.oetest import runTests
from oeqa.utils.sshcontrol import SSHControl
from oeqa.utils.dump import get_host_dumper

# this isn't pretty but we need a fake target object
# for running the tests externally as we don't care
# about deploy/start we only care about the connection methods (run, copy)
class FakeTarget(object):
    def __init__(self, d):
        self.connection = None
        self.ip = None
        self.server_ip = None
        self.datetime = time.strftime('%Y%m%d%H%M%S',time.gmtime())
        self.testdir = d.getVar("TEST_LOG_DIR", True)
        self.pn = d.getVar("PN", True)

    def exportStart(self):
        self.sshlog = os.path.join(self.testdir, "ssh_target_log.%s" % self.datetime)
        sshloglink = os.path.join(self.testdir, "ssh_target_log")
        if os.path.lexists(sshloglink):
            os.remove(sshloglink)
        os.symlink(self.sshlog, sshloglink)
        print("SSH log file: %s" %  self.sshlog)
        self.connection = SSHControl(self.ip, logfile=self.sshlog)

    def run(self, cmd, timeout=None):
        return self.connection.run(cmd, timeout)

    def copy_to(self, localpath, remotepath):
        return self.connection.copy_to(localpath, remotepath)

    def copy_from(self, remotepath, localpath):
        return self.connection.copy_from(remotepath, localpath)


class MyDataDict(dict):
    def getVar(self, key, unused = None):
        return self.get(key, "")

class TestContext(object):
    def __init__(self):
        self.d = None
        self.target = None

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--target-ip", dest="ip", help="The IP address of the target machine. Use this to \
            overwrite the value determined from TEST_TARGET_IP at build time")
    parser.add_argument("-s", "--server-ip", dest="server_ip", help="The IP address of this machine. Use this to \
            overwrite the value determined from TEST_SERVER_IP at build time.")
    parser.add_argument("-d", "--deploy-dir", dest="deploy_dir", help="Full path to the package feeds, that this \
            the contents of what used to be DEPLOY_DIR on the build machine. If not specified it will use the value \
            specified in the json if that directory actually exists or it will error out.")
    parser.add_argument("-l", "--log-dir", dest="log_dir", help="This sets the path for TEST_LOG_DIR. If not specified \
            the current dir is used. This is used for usually creating a ssh log file and a scp test file.")
    parser.add_argument("--list-tests", dest="list_tests", help="This lists the current TEST_SUITES that will be run.", action='store_true')
    parser.add_argument("-r","--run-tests", dest="run_tests", help="Overwrite TEST_SUITES from the json file with custom list of tests.", nargs = '*')
    parser.add_argument("-m","--machine", dest="machine", help="Overwrite MACHINE from the json file ")
    parser.add_argument("json", help="The json file exported by the build system", default="testdata.json", nargs='?')

    args = parser.parse_args()

    os.environ["bin_dir"] = os.path.join(os.getcwd(), "binaries") # exporting bin_dir path

    if os.path.isdir("extralayers"):
        extrapaths = [x[0] for x in os.walk('extralayers')]
        for path in extrapaths:
            if os.path.isdir(os.path.join(path,"oeqa")) and (os.path.join(path,"oeqa") not in sys.path):
                sys.path.append(os.path.abspath(path))

    with open(args.json, "r") as f:
        loaded = json.load(f)

    if args.ip:
        loaded["target"]["ip"] = args.ip
    if args.server_ip:
        loaded["target"]["server_ip"] = args.server_ip

    d = MyDataDict()
    for key in loaded["d"].keys():
        d[key] = loaded["d"][key]

    if args.log_dir:
        d["TEST_LOG_DIR"] = args.log_dir
    else:
        d["TEST_LOG_DIR"] = os.path.abspath(os.path.dirname(__file__))
    if args.deploy_dir:
        d["DEPLOY_DIR"] = args.deploy_dir
    else:
        if not os.path.isdir(d["DEPLOY_DIR"]):
            print("WARNING: The path to DEPLOY_DIR does not exist: %s" % d["DEPLOY_DIR"])


    target = FakeTarget(d)
    for key in loaded["target"].keys():
        setattr(target, key, loaded["target"][key])

    host_dumper = get_host_dumper(d)
    host_dumper.parent_dir = loaded["host_dumper"]["parent_dir"]
    host_dumper.cmds = loaded["host_dumper"]["cmds"]

    tc = TestContext()
    setattr(tc, "d", d)
    setattr(tc, "target", target)
    setattr(tc, "host_dumper", host_dumper)
    for key in loaded.keys():
        if key != "d" and key != "target" and key != "host_dumper":
            setattr(tc, key, loaded[key])

    if args.machine:
        d['MACHINE'] = args.machine
        bin_dir = os.getenv("bin_dir")
        found = False
        if os.path.exists(bin_dir):
            for item in os.listdir(bin_dir):
                if not re.search("native", item) and os.path.exists(os.path.join(bin_dir, item, "mapping.cfg")):
                    with open(os.path.join(bin_dir, item, "mapping.cfg"), "r") as mapping_file:
                        mapping = eval(mapping_file.read())
                        if args.machine in mapping.keys():
                            d['TARGET_SYS'] = mapping[args.machine][0]
                            d['TUNE_FEATURES'] = mapping[args.machine][1]
                            found = True
        if not found:
            print("WARNING: Cannot find binaries for provided machine %s." % args.machine)

    if args.run_tests:
        tc.testslist = args.run_tests

    if args.list_tests:
        for test in tc.testslist:
            print test
    else:
        for index, test in enumerate(tc.testslist):
            if os.path.isdir(os.sep.join(test.split('.'))):
                del tc.testslist[index]
                for files in os.listdir(os.sep.join(test.split('.'))):
                    if (files.endswith(".py")) and not files.startswith("_"):
                        tc.testslist.insert(index, test+'.'+files.split('.')[0])
            elif not os.path.isfile(os.path.join(os.sep.join(test.split('.')), '.py')):
                for testpath in sys.path:
                    directory = os.path.join(testpath, os.sep.join(test.split('.')))
                    if os.path.isdir(directory):
                        del tc.testslist[index]
                        for files in os.listdir(directory):
                            if (files.endswith(".py")) and not files.startswith("_"):
                                tc.testslist.insert(index, test+'.'+files.split('.')[0])
        target.exportStart()
        runTests(tc)

    return 0

if __name__ == "__main__":
    try:
        ret = main()
    except Exception:
        ret = 1
        import traceback
        traceback.print_exc(5)
    sys.exit(ret)
