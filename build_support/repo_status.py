import git, os
import xml.etree.ElementTree as ET

from . import ProjectMap

class _ProjectBranch:
    def __init__(self, projectName):
        # default to master branch
        self.branch = "origin/master"
        self.name = projectName
        self.sha = None

class _BranchSpecification:
    """This class tracks a "branch set" in the build's git repositories
    which define a single logical build.  A change to any of the
    branches will result in a world build.

    """
    def __init__(self, branch_tag, repos):
        self._project_branches = {}
        self.name = branch_tag.attrib["name"]
        self.project = branch_tag.attrib["project"]

        # by default, all repos are at origin/master
        for (name, _) in repos.iteritems():
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
        for (_, branch) in self._project_branches.iteritems():
            assert (repos.has_key(branch.name))
            repo = repos[branch.name]
            for remote in repo.remotes:
                remote.fetch()
            branch.sha = str(repo.commit(branch.branch))
        
    def needs_build(self, repos):
        # checks the commits on the branch repos to see if they have
        # been updated.
        for (_, branch) in self._project_branches.iteritems():
            repo = repos[branch.name]
            for remote in repo.remotes:
                remote.fetch()
            if branch.sha != str(repo.commit(branch.branch)):
                return True
            return False

class RepoStatus:
    def __init__(self, buildspec):

        # all repositories are cloned into this dir, so they can be cleaned up
        self._repo_dir = ProjectMap().source_root() + "/repos"
        
        # key is project, value is repo object
        self._repos = {}

        self._branches = []

        buildspec = ET.parse(buildspec)
        branches = buildspec.find("branches")
        repos = buildspec.find("repos")

        # fetch all the repos into _repo_dir
        for tag in repos:
            url = tag.attrib["repo"]
            project = tag.tag
            if (self._repos.has_key(project)):
                continue

            project_repo_dir = self._repo_dir + "/" + project
            repo = None
            if not os.path.exists(project_repo_dir):
                os.makedirs(project_repo_dir)
                repo = git.Repo.clone_from(url, project_repo_dir)
            else:
                repo = git.Repo(project_repo_dir)
                for remote in repo.remotes:
                    remote.fetch()
            self._repos[project] = repo

        for branch in branches.findall("branch"):
            self._branches.append(_BranchSpecification(branch, self._repos))


    def poll(self):
        """returns list of branches that should be triggered"""
        ret_list = []
        for branch in self._branches:
            if branch.needs_build(self._repos):
                ret_list.append(branch.name)
                branch.update_commits(self._repos)
        return ret_list
                
            
