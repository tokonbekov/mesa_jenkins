import tempfile, shutil, git
import xml.etree.ElementTree as ET


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
            repo.remotes[0].fetch()
            branch.sha = str(repo.commit("origin/" + branch.branch))
        
    def needs_build(self, repos):
        # checks the commits on the branch repos to see if they have
        # been updated.
        for (_, branch) in self._project_branches.iteritems():
            repo = repos[branch.repo_url]
            repo.remotes[0].fetch()
            if branch.sha != str(repo.commit("origin/" + branch.branch)):
                return True
            return False

class RepoStatus:
    def __init__(self, buildspec):

        # all repositories are cloned into this dir, so they can be cleaned up
        self._tmp_dir = tempfile.mkdtemp()
        
        # key is url, value is repo object
        self._repos = {}

        self._branches = []

        buildspec = ET.parse(buildspec)
        branches = buildspec.find("branches")
        default = branches.find("default")

        # clone all the repos into _tmp_dir
        for tag in default:
            url = tag.attrib["repo"]
            if (self._repos.has_key(url)):
                continue

            tmp_dir = tempfile.mkdtemp(dir=self._tmp_dir)
            repo = git.Repo.clone_from(url, tmp_dir)
            self._repos[url] = repo

        for branch in branches:
            for tag in branch:
                if not tag.attrib.has_key("repo"):
                    continue
                url = tag.attrib["repo"]
                if self._repos.has_key(url):
                    continue
                # else this branch is in a new repository
                tmp_dir = tempfile.mkdtemp(dir=self._tmp_dir)
                repo = git.Repo.clone_from(url, tmp_dir)
                self._repos[url] = repo
        
        for branch in branches.findall("branch"):
            self._branches.append(_BranchSpecification(branch, default, self._repos))


    def __del__(self):
        shutil.rmtree(self._tmp_dir)
        

    def poll(self):
        """returns list of branches that should be triggered"""
        ret_list = []
        for branch in self._branches:
            if branch.needs_build(self._repos):
                ret_list.append(branch.name)
                branch.update_commits(self._repos)
        return ret_list
                
            
