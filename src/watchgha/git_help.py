"""
Get information from local git.
"""

import dulwich.porcelain
import dulwich.repo

_repo = None

def _dulwich_repo(dir="."):
    global _repo
    if _repo is None:
        _repo = dulwich.repo.Repo(dir)
    return _repo

def git_repo_url(dir):
    return dulwich.porcelain.get_remote_repo(_dulwich_repo(dir))[1]

def git_branch():
    return dulwich.porcelain.active_branch(_dulwich_repo()).decode()
