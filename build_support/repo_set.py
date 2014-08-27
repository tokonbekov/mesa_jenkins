import git, os, time, json, hashlib
import xml.etree.ElementTree as ET

from . import ProjectMap
from . import Options

class _ProjectBranch:
    def __init__(self, projectName):
        # default to master branch
        self.branch = "origin/master"
        self.name = projectName
        self.sha = None

class BranchSpecification:
    """This class tracks a "branch set" in the build's git repositories
    which define a single logical build.  A change to any of the
    branches will result in a world build.

    """
    def __init__(self, branch_tag, repos=None):
        self._project_branches = {}
        self.name = branch_tag.attrib["name"]
        self.project = branch_tag.attrib["project"]
        if not repos:
            repos = RepoSet()
        self._repos = repos

        # by default, all repos are at origin/master
        for name in repos.projects():
            pb = _ProjectBranch(name)
            self._project_branches[name] = pb

        # override the defaults
        for a_project in branch_tag:
            name = a_project.tag
            assert(self._project_branches.has_key(name))
            self._project_branches[name].branch = a_project.attrib["branch"]

        for (_, branch) in self._project_branches.iteritems():
            repo = repos.repo(branch.name)
            branch.sha = repo.commit(branch.branch).hexsha

    def update_commits(self):
        # get the current commit for each project
        self._repos.fetch()
        for (_, branch) in self._project_branches.iteritems():
            repo = self._repos.repo(branch.name)
            branch.sha = repo.commit(branch.branch).hexsha
        
    def needs_build(self):
        # checks the commits on the branch repos to see if they have
        # been updated.
        self._repos.fetch()
        for (_, branch) in self._project_branches.iteritems():
            repo = self._repos.repo(branch.name)
            hexsha = repo.commit(branch.branch).hexsha
            if branch.sha != hexsha:
                return branch.name + "-" + repo.git.rev_parse(hexsha, short=True)
        return False

    def checkout(self):
        """checks out the specified branches for each repository in the branch
        set """
        for (name, branch) in self._project_branches.iteritems():
            repo = self._repos.repo(name)
            repo.git.checkout(branch.branch)

class RepoSet:
    """this class represents the set of git repositories which are
    specified in the build_specification.xml file."""
    def __init__(self):
        buildspec = ProjectMap().build_spec()
        self._repos = {}
        if type(buildspec) == str:
            buildspec = ET.parse(buildspec)
        repo_dir = ProjectMap().source_root() + "/repos"
        repos = buildspec.find("repos")

        # fetch all the repos into _repo_dir
        for tag in repos:
            url = tag.attrib["repo"]
            project = tag.tag

            assert ( not self._repos.has_key(project)) # double entry

            project_repo_dir = repo_dir + "/" + project
            if not os.path.exists(project_repo_dir):
                os.makedirs(project_repo_dir)
                print "cloning " + url
                git.Repo.clone_from(url, project_repo_dir)
            repo = git.Repo(project_repo_dir)
            self._repos[project] = repo

    def repo(self, project_name):
        return self._repos[project_name]

    def projects(self):
        return self._repos.keys()

    def fetch(self):
        for repo in self._repos.values():
            for remote in repo.remotes:
                print "fetching " + remote.url
                remote.fetch()
        # the fetch has left our repo objects in an inconsistent
        # state.  We need to recreate them.
        self.__init__()

class RevisionSpecification:
    def __init__(self, from_string=None, from_cmd_line=None):
        # key is project, value is revision
        self._revisions = {}

        if from_string is not None:
            self.from_string(from_string)
            return

        if from_cmd_line is not None:
            self.from_cmd_line_param(from_cmd_line)
            return

        repo_set = RepoSet()
        projects = repo_set.projects()
        for p in projects:
            repo = repo_set.repo(p)
            rev = repo.git.rev_parse("HEAD", short=True)
            self._revisions[p] = rev

    def from_string(self, spec):
        if type(spec) == str:
            spec = ET.fromstring(spec)
        assert(spec.tag == "RevSpec")
        self._revisions = spec.attrib

    def to_cmd_line_param(self):
        revs = [project + "=" + rev for (project, rev) in self._revisions.iteritems()]
        return " ".join(revs)

    def from_cmd_line_param(self, params):
        revs = []
        for rev in params:
            rev = rev.split("=")
            rev[1] = '"' + rev[1] + '"'
            revs.append(rev[0] + "=" + rev[1])
        rev_text = "<RevSpec " + " ".join(revs) + "/>"
        rs = self.from_string(rev_text)

    def __str__(self):
        projects = self._revisions.keys()
        projects.sort()
        tag = ET.Element("RevSpec")
        for p in projects:
            tag.set(p, self._revisions[p])
        return ET.tostring(tag)
        
    def checkout(self):
        repo_set = RepoSet()
        for (project, revision) in self._revisions.iteritems():
            project_repo = repo_set.repo(project)
            project_repo.git.checkout(revision)

class RepoStatus:
    def __init__(self, buildspec=None):
        if not buildspec:
            buildspec = ProjectMap().build_spec()
        if type(buildspec) == str:
            buildspec = ET.parse(buildspec)

        # key is project, value is repo object
        self._repos = RepoSet()

        self._branches = []

        branches = buildspec.find("branches")

        for branch in branches.findall("branch"):
            self._branches.append(BranchSpecification(branch, self._repos))


    def poll(self):
        """returns list of branches that should be triggered"""
        ret_dict = {}
        for branch in self._branches:
            trigger_commit = branch.needs_build()
            if trigger_commit:
                ret_dict[branch.name] = trigger_commit
                branch.update_commits()
        return ret_dict

class BuildSpecification:
    def __init__(self, buildspec=None):
        if not buildspec:
            buildspec = ProjectMap().build_spec()
        if type(buildspec) == str:
            buildspec = ET.parse(buildspec)

        self._buildspec = buildspec
        self._reposet = RepoSet()
        self._branch_specs = {}

        branches = buildspec.find("branches")
        for abranch in branches.findall("branch"):
            branch = BranchSpecification(abranch, self._reposet)
            self._branch_specs[branch.name] = branch

    def branch_specification(self, branch_name):
        return self._branch_specs[branch_name]

    def checkout(self, branch_name):
        self._branch_specs[branch_name].checkout()

class ProjectInvoke:
    """this object summarizes the component and all options required to
    invoke a build on a single project.  Invocation can take place
    locally or on CI.  ProjectInvoke supports writing status files for
    the invoked build to a network folder, to prevent duplicate builds.

    """

    def __init__(self, options=None, revision_spec=None, 
                 project=None, from_string=None):
        if from_string:
            self.from_string(from_string)
            return

        if not options:
            options = Options()
        self.options = options

        if not project:
            project=ProjectMap().current_project()
        self.project = project

        if not revision_spec:
            revision_spec = RevisionSpecification()
        self.revision_spec = revision_spec

    def __str__(self):
        tag = ET.Element("ProjectInvoke")
        tag.set("Project", self.project)
        tag.append(ET.fromstring(str(self.revision_spec)))
        tag.append(self.options.to_elementtree())
        return ET.tostring(tag)

    def from_string(self, string):
        tag = ET.fromstring(string)
        self.project = tag.attrib["Project"]
        self.options = Options(from_xml=tag.find("Options"))
        revtag = tag.find("RevSpec")
        self.revision_spec = RevisionSpecification(from_string=revtag)
        
        
    def info_file(self):
        o = self.options
        return "/".join([o.result_path, 
                         self.project,
                         o.arch,
                         o.config,
                         o.hardware, 
                         "_build_info.txt"])

    def _read_info(self):
        """returns a dictionary of status content"""
        info_file = self.info_file()
        if not os.path.exists(info_file):
            # sometimes network/mount hiccups make it seem like the
            # file is not there
            time.sleep(1)
            if not os.path.exists(info_file):
                return {}
            print "WARN: network hiccup detected"

        attempt_number = 0
        while attempt_number < 5:
            attempt_number += 1
            try:
                info_text = open(info_file, "r").read()
                info_dict = json.loads(info_text)
                return info_dict
            except:
                # network hiccup
                time.sleep(5)

        # failed to parse several times.
        return {}

    def _write_info(self, info_dict):
        info_file = self.info_file()
        info_dir = os.path.dirname(info_file)
        if not os.path.exists(info_dir):
            try:
                os.makedirs(info_dir)
            except:
                # race condition means some other build may have
                # created the directory.
                pass
        open(info_file, "w").write(json.dumps(info_dict))

    def get_info(self, key, block=True):
        for _ in range(0,10):
            info = self._read_info()
            if info.has_key(key):
                return info[key]
            if not block:
                return None
            # possible that the data has not been flushed to the
            # server
            time.sleep(1)

    def set_info(self, key, value):
        info_dict = self._read_info()
        info_dict[key] = value
        self._write_info(info_dict)

    def hash(self, salt):
        """provides a string value to uniquely identify a build.  This is used
        to find builds and resolve clashes between similar builds on
        the jenkins server"""
        return hashlib.md5(salt + str(self)).hexdigest()
        
    def to_short_string(self):
        return " ".join([self.project,
                         self.options.arch, 
                         self.options.config, 
                         self.options.hardware])
