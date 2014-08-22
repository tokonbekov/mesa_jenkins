import git, os
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
    def __init__(self, branch_tag, repos):
        self._project_branches = {}
        self.name = branch_tag.attrib["name"]
        self.project = branch_tag.attrib["project"]

        # by default, all repos are at origin/master
        for name in repos.projects():
            pb = _ProjectBranch(name)
            self._project_branches[name] = pb

        # override the defaults
        for a_project in branch_tag:
            name = a_project.tag
            assert(self._project_branches.has_key(name))
            self._project_branches[name].branch = a_project.attrib["branch"]

        self.update_commits(repos)

    def update_commits(self, repos):
        # get the current commit for each project
        repos.fetch()
        for (_, branch) in self._project_branches.iteritems():
            repo = repos.repo(branch.name)
            branch.sha = repo.commit(branch.branch).hexsha
        
    def needs_build(self, repos):
        # checks the commits on the branch repos to see if they have
        # been updated.
        repos.fetch()
        for (_, branch) in self._project_branches.iteritems():
            repo = repos.repo(branch.name)
            if branch.sha != repo.commit(branch.branch).hexsha:
                return True
        return False

    def checkout(self, repos):
        """checks out the specified branches for each repository in the branch
        set"""
        for (name, branch) in self._project_branches.iteritems():
            repo = repos.repo(name)
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
                remote.fetch()

class RevisionSpecification:
    def __init__(self, from_string=None):
        # key is project, value is revision
        self._revisions = {}

        if from_string is not None:
            self.from_string(from_string)
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

    def __str__(self):
        projects = self._revisions.keys()
        projects.sort()
        tag = ET.Element("RevSpec")
        for p in projects:
            tag.set(p, self._revisions[p])
        return ET.tostring(tag)
        

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
        ret_list = []
        for branch in self._branches:
            if branch.needs_build(self._repos):
                ret_list.append(branch.name)
                branch.update_commits(self._repos)
        return ret_list

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
        self._branch_specs[branch_name].checkout(self._reposet)

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
        self._revision_spec = revision_spec

    def __str__(self):
        tag = ET.Element("ProjectInvoke")
        tag.set("Project", self.project)
        tag.append(ET.fromstring(str(self._revision_spec)))
        tag.append(self.options.to_elementtree())
        return ET.tostring(tag)

    def from_string(self, string):
        tag = ET.fromstring(string)
        self.project = tag.attrib["Project"]
        self.options = Options(from_xml=tag.find("Options"))
        revtag = tag.find("RevSpec")
        self._revision_spec = RevisionSpecification(from_string=revtag)
        
        
    def get_info(self, key, block=True):
        # for _ in range(0,10):
        #     info = self._read_info()
        #     if info.has_key(key):
        #         return info[key]
        #     if not block:
        #         return None
        #     # possible that the data has not been flushed to the
        #     # server
        #     time.sleep(1)
        return None

    def set_info(self, key, value):
        # info_dict = self._read_info()
        # info_dict[key] = value
        # self._write_info(info_dict)
        pass
