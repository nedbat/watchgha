"""
Get information from local git.
"""

import functools

import dulwich.porcelain
import dulwich.repo


@functools.lru_cache(maxsize=10)
def _dulwich_repo(dir="."):
    return dulwich.repo.Repo(dir)


def git_repo_urls(dir):
    """Find all the remote URLs for a git repo at `dir`."""
    config = _dulwich_repo(dir).get_config()
    for section in config.sections():
        if section[0] == b"remote":
            url = config.get(section, "url").decode()
            yield url


def git_branch(dir):
    """Get the current git branch name."""
    return dulwich.porcelain.active_branch(_dulwich_repo(dir)).decode()
