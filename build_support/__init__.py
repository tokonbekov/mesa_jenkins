#!/usr/bin/python

import time
from command import rmtree
from command import run_batch_command
from command import rmfile
#from command import killMajorProcesses
from options import Options
from project_map import ProjectMap
#from export import Export
#from export import ExportTest
#from export import ExportSymbols
#from jenkins import Jenkins
#from spec import BuildInvoke
#from spec import BuildSpec
#from export import ExportZip
#from gtest import GTest as GTest
#from clean_server import CleanServer
from timer import TimeOut
from repo_set import *
from dependency_graph import DependencyGraph
from export import Export
from builders import *
from jenkins import *

class DefaultTimeout:
    def __init__(self, options=None):
        self._options = options
        if not options:
            self._options = Options()

    def GetDuration(self):
        """by default, components should finish in under 15 minutes.
        For daily builds, 60 minutes is acceptable."""

        if self._options.type == "daily" or self._options.type == "release":
            return 60
        return 15

def null_build():
    pass

class NullInvoke:
    """masquerades as an invoke object, so the main routine can post
    results even if there is no server to post to"""
    def __init__(self):
        pass
    
    def set_info(self, *args):
        pass

    def set_status(self, *args):
        pass

def build(builder, options=None, time_limit=None):
    if not time_limit:
        time_limit = DefaultTimeout()
    if not options:
        options = Options()
    action_map = {
               "build": builder.build,
               "clean": builder.clean,
               "test" : builder.test,
              }
    actions = options.action

    invoke = NullInvoke()

    # TODO: add this stuff
    if (options.result_path):
        # if we aren't posting to a server, don't attempt to write
        # status
        invoke = ProjectInvoke(options)

    invoke.set_info("start_time", time.time())

    # start a thread to limit the run-time of the build
    to = TimeOut(time_limit)
    to.start()


    if type(actions) is str:
        actions = [actions]

    for a in actions:
        options.action = a

        if options.action in action_map:
            try:
                action_map[options.action]()
            except:
                # we need to cancel the timer first, in case
                # set_status fails, and the timer is left running
                to.end()
                invoke.set_info("status", "failed")
                # must cancel timeout timer, which will prevent process from ending
                raise        
                
    # must cancel timeout timer, which will prevent process from
    # ending.  cancel the timer first, in case set_status fails, and
    # the timer is left running
    to.end()
    invoke.set_info("end_time", time.time())
    invoke.set_info("status", "success")


