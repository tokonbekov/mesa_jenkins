# Copyright (C) Intel Corp.  2014.  All Rights Reserved.

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice (including the
# next paragraph) shall be included in all copies or substantial
# portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE COPYRIGHT OWNER(S) AND/OR ITS SUPPLIERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#  **********************************************************************/
#  * Authors:
#  *   Mark Janes <mark.a.janes@intel.com>
#  **********************************************************************/

import sys
from . import ProjectInvoke
from . import ProjectMap

class DependencyGraph:
    """Calculates build order for all prerequisites"""
    def __init__(self, components, options):

        # The key of the graph dict is ProjectInvoke hash string, and
        # the value is a list of ProjectInvoke hashes that it depends on
        self._dependency_graph = {}

        # List of build invoke objects that are complete
        self._completed_builds = []

        # Key is a build invoke, value is a list of build invokes that
        # require it
        self._completion_graph = {}

        # key is project name, value is project tag
        self._project_tags = {}
        build_spec = ProjectMap().build_spec()
        projects = build_spec.find("projects")
        for project in projects.findall("project"):
            self._project_tags[project.attrib["name"]] = project

        # build up the dependency_graph
        if type(components) != type([]):
            components = [components]
        for a_component in components:
            bi = ProjectInvoke(project=a_component, 
                               options=options)
            self._add_to_graph(bi)

        if not self._dependency_graph.items():
            print "ERROR: no builds in dependency graph"
            sys.exit(-1)

        # build up the completion_graph
        for (component, prereqs) in self._dependency_graph.items():
            if not self._completion_graph.has_key(component):
                self._completion_graph[component] = []
            for a_prereq in prereqs:
                if not self._completion_graph.has_key(a_prereq):
                    self._completion_graph[a_prereq] = []
                if component not in self._completion_graph[a_prereq]:
                    self._completion_graph[a_prereq].append(component)

    def ready_builds(self):
        """provide a list of builds which have all prerequisites
        satisfied."""
        ret_list = []
        for (component, prereqs) in self._dependency_graph.iteritems():
            if not prereqs:
                ret_list.append(ProjectInvoke(from_string=component))

        return ret_list

    def build_complete(self, build):
        """notifies the DependencyGraph that a build has completed.
        Makes other builds available via ready_builds"""
        build = str(build)
        del self._dependency_graph[build]
        for an_unblocked_component in self._completion_graph[build]:
            if an_unblocked_component in self._dependency_graph:
                self._dependency_graph[an_unblocked_component].remove(build)
        del self._completion_graph[build]

    @classmethod
    def long_pole(cls, invoke):
        """returns a list of invokes composing the long pole of the build"""
        depGraph = cls(invoke.project, 
                       invoke.options)
        blocking_builds = [invoke]
        while True:
            last_build = None
            last_finish_time = 0
            for a_dep in depGraph._dependency_graph[str(invoke)]:
                a_dep = ProjectInvoke(from_string=a_dep)
                end_time = a_dep.get_info("end_time")
                if not end_time:
                    continue
                if end_time > last_finish_time:
                    last_build = a_dep
                    last_finish_time = end_time
            if not last_build:
                return blocking_builds
            blocking_builds.append(last_build)
            invoke = last_build
        

    def _prereqs(self, project_invoke):
        results = []

        tags = self._project_tags[project_invoke.project]
        for a_prereq in tags.findall("prerequisite"):
            # make a deep copy of the project_invoke, which will be
            # updated by the prereq

            # allow the build specification to make prerequisites
            # contingent on the type.  If type is specified for the
            # prereq, then it is only built for matching types.
            attrib = a_prereq.attrib
            if attrib.has_key("only_for_type"):
                types = attrib["only_for_type"].split(",")
                if project_invoke.options.type not in types:
                    continue

            arches = [project_invoke.options.arch]
            if attrib.has_key("arch"):
                arches = attrib["arch"].split(",")
            hardwares = [project_invoke.options.hardware]
            if attrib.has_key("hardware"):
                hardwares = attrib["hardware"].split(",")
            for arch in arches:
                for hardware in hardwares:
                    shards = ["0"]
                    p_shard = "0"
                    if a_prereq.attrib.has_key("shard"):
                        p_shard = a_prereq.attrib["shard"]
                    if p_shard != "0" and ":" not in p_shard:
                        i_shards = range(0,int(p_shard))
                        shards = [str(s + 1) + ":" + p_shard for s in i_shards]
                    for shard in shards:
                        pistr = str(project_invoke)
                        prereq_invoke = ProjectInvoke(from_string=pistr)
                        prereq_invoke.project = attrib["name"]
                        prereq_invoke.options.hardware = hardware
                        prereq_invoke.options.arch = arch
                        prereq_invoke.options.shard = shard
                        results.append(prereq_invoke)

        return results


    def _add_to_graph(self, project_invoke):
        """adds the build_invoke and all prerequisites to the
        _dependency_graph"""
        shard = project_invoke.options.shard
        if shard != "0" and ":" not in shard:
            for i in range(0,int(shard)):
                # make a deep copy of the project invoke
                p = ProjectInvoke(from_string=str(project_invoke))
                p.shard = str(i + 1) + ":" + str(shard)
                self._add_to_graph(p)
        
        graph = self._dependency_graph
        if graph.has_key(str(project_invoke)):
            # multiple dependencies on this invocation, which has
            # already been calculated in the graph
            return
        graph[str(project_invoke)] = []

        prereqs = self._prereqs(project_invoke)

        for pre_invoke in prereqs:
            
            # add current dependency to graph
            graph[str(project_invoke)].append(str(pre_invoke))

            # recursively add dependencies
            self._add_to_graph(pre_invoke)
