import sys, os
import xml.etree.ElementTree as ET

from . import Options

class ProjectMap:
    """provides convenient and consistent access to paths which are
    necessary to the builds"""

    def __init__(self):
        """locate the build specification document, to use as a reference
        point for all other paths"""
        root = os.path.dirname(os.path.abspath(sys.argv[0]))
        if "py.test" in sys.argv[0]:
            root = os.getcwd()
        while True:
            build_spec = root + "/build_specification.xml"
            if not os.path.exists(build_spec):
                if (os.path.dirname(root) == root):
                    # we are at "/"
                    assert(False)
                    return

                root = os.path.dirname(root)
                continue

            # else we have found the spec
            self._source_root = root
            return

    def source_root(self):
        """top directory, which contains the build_specification.xml"""
        return self._source_root

    def build_root(self):
        """chroot directory where all results are placed during a build"""
        br = self._source_root + "/build_root/" + Options().arch
        if not os.path.exists(br):
            os.makedirs(br)
        return br

    def project_build_dir(self, project):
        """location of the build.py for the project"""
        cb = self._source_root + "/" + project
        assert(os.path.exists(cb))
        return cb

    def project_source_dir(self, project):
        """location of the git repo for the project"""
        sdir = self._source_root + "/repos/" + project
        assert(os.path.exists(sdir))
        return sdir

    def current_project(self):
        """name of the project which is invoking this method"""
        build_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.split(build_dir)[1]

    def output_dir(self):
        """logs / test xml go in this directory"""
        o = Options()
        if o.result_path:
            return os.path.abspath(o.result_path)
        return self._source_root + "/results"

    def build_spec(self):
        return ET.parse(self.source_root() + "/build_specification.xml")
