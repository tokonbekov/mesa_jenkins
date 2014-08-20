import git, os
import xml.etree.ElementTree as ET

from . import ProjectMap

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
            repo.git.checkout(b=branch.branch)

class RepoSet:
    """this class represents the set of git repositories which are
    specified in the build_specification.xml file."""
    def __init__(self, buildspec):
        self._repos = {}
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


class RepoStatus:
    def __init__(self, buildspec):
        buildspec = ET.parse(buildspec)

        # key is project, value is repo object
        self._repos = RepoSet(buildspec)

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
                
            
