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


def git_repo_urls(dir):
    """Find all the remote URLs for a git repo at `dir`."""
    config = _dulwich_repo(dir).get_config()
    for section in config.sections():
        if section[0] == b"remote":
            url = config.get(section, "url").decode()
            yield url


def git_branch():
    """Get the current git branch name."""
    return dulwich.porcelain.active_branch(_dulwich_repo()).decode()
