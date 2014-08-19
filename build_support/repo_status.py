import git, os
import xml.etree.ElementTree as ET

from . import ProjectMap

class _ProjectBranch:
    def __init__(self, tag):
        self.name = str(tag.tag)
        self.repo_url = None
        self.branch = None
        self.sha = None
        if tag.attrib.has_key("repo"):
            self.repo_url = tag.attrib["repo"]
        if tag.attrib.has_key("branch"):
            self.branch = tag.attrib["branch"]

class _BranchSpecification:
    """This class tracks a "branch set" in the build's git repositories
    which define a single logical build.  A change to any of the
    branches will result in a world build.

    """
    def __init__(self, spec_tag, default_tag, repos):
        self._project_branches = {}
        self.name = spec_tag.attrib["name"]

        # start with the defaults
        for a_project in default_tag:
            pb = _ProjectBranch(a_project)
            self._project_branches[pb.name] = pb

        # override the defaults
        for a_project in spec_tag:
            pb = _ProjectBranch(a_project)
            if (pb.repo_url):
                self._project_branches[pb.name].repo_url = pb.repo_url
            if (pb.branch):
                self._project_branches[pb.name].branch = pb.branch

        self.update_commits(repos)

    def update_commits(self, repos):
        # get the current commit for each project
        for (_, branch) in self._project_branches.iteritems():
            assert (repos.has_key(branch.repo_url))
            repo = repos[branch.repo_url]
            for remote in repo.remotes:
                remote.fetch()
            branch.sha = str(repo.commit(branch.branch))
        
    def needs_build(self, repos):
        # checks the commits on the branch repos to see if they have
        # been updated.
        for (_, branch) in self._project_branches.iteritems():
            repo = repos[branch.repo_url]
            for remote in repo.remotes:
                remote.fetch()
            if branch.sha != str(repo.commit(branch.branch)):
                return True
            return False

class RepoStatus:
    def __init__(self, buildspec):

        # all repositories are cloned into this dir, so they can be cleaned up
        self._repo_dir = ProjectMap().source_root() + "/repos"
        
        # key is url, value is repo object
        self._repos = {}

        self._branches = []

        buildspec = ET.parse(buildspec)
        branches = buildspec.find("branches")
        default = branches.find("default")

        # fetch all the repos into _repo_dir
        for tag in default:
            url = tag.attrib["repo"]
            if (self._repos.has_key(url)):
                continue

            project_repo_dir = self._repo_dir + "/" + tag.tag
            repo = None
            if not os.path.exists(project_repo_dir):
                os.makedirs(project_repo_dir)
                repo = git.Repo.clone_from(url, project_repo_dir)
            else:
                repo = git.Repo(project_repo_dir)
                for remote in repo.remotes:
                    remote.fetch()
            self._repos[url] = repo

        for branch in branches:
            for tag in branch:
                if not tag.attrib.has_key("repo"):
                    continue
                url = tag.attrib["repo"]
                assert (self._repos.has_key(url))
        
        for branch in branches.findall("branch"):
            self._branches.append(_BranchSpecification(branch, default, self._repos))


    def poll(self):
        """returns list of branches that should be triggered"""
        ret_list = []
        for branch in self._branches:
            if branch.needs_build(self._repos):
                ret_list.append(branch.name)
                branch.update_commits(self._repos)
        return ret_list
                
            
