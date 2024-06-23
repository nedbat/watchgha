import pytest

from watchgha import watch_runs
from watchgha.watch_runs import gha_urls


def fake_isdir(path):
    return path == "." or path.startswith("dir")


FAKE_REPOS = {
    ".": {
        "urls": [
            "https://github.com/owner/repo.git",
        ],
        "branch": "mainbranch",
    },
    "dir1": {
        "urls": [
            "git@github.com:somebody/therepo.git",
        ],
        "branch": "joe/feature1",
    },
    "dir-many-remotes": {
        "urls": [
            "https://gitlab.com/maintainer/project.git",
            "https://github.com/contributor1/project",
            "https://github.com/contributor2/project.git",
        ],
        "branch": "main",
    },
    "dir-only-gitlab": {
        "urls": [
            "https://gitlab.com/maintainer/project.git",
        ],
    },
    "dir-enterprise": {
        "urls": [
            "https://mygithub.enterprise.com/me/myproject",
        ],
    },
    "dir-bug22": {
        "urls": [
            "git@git.mydomain.com:davidszotten/davidrepo",
        ],
    },
}


def fake_git_repo_urls(repo):
    return FAKE_REPOS.get(repo, {}).get("urls", ())


def fake_git_branch(repo):
    return FAKE_REPOS.get(repo, {}).get("branch", "master")


@pytest.fixture
def mocked_gha_urls_dependencies(monkeypatch):
    monkeypatch.setattr(watch_runs, "isdir", fake_isdir)
    monkeypatch.setattr(watch_runs, "git_repo_urls", fake_git_repo_urls)
    monkeypatch.setattr(watch_runs, "git_branch", fake_git_branch)


@pytest.mark.parametrize(
    "args, evars, urls",
    [
        (
            ["."],
            {},
            [
                "https://api.github.com/repos/owner/repo/actions/runs?per_page=100&branch=mainbranch",
            ],
        ),
        (
            ["dir1"],
            {},
            [
                "https://api.github.com/repos/somebody/therepo/actions/runs?per_page=100&branch=joe%2Ffeature1",
            ],
        ),
        (
            ["dir1", "another-branch"],
            {},
            [
                "https://api.github.com/repos/somebody/therepo/actions/runs?per_page=100&branch=another-branch",
            ],
        ),
        (
            ["dir1", None, "sha12345678"],
            {},
            [
                "https://api.github.com/repos/somebody/therepo/actions/runs?per_page=100&head_sha=sha12345678",
            ],
        ),
        (
            ["dir-many-remotes"],
            {},
            [
                "https://api.github.com/repos/contributor1/project/actions/runs?per_page=100&branch=main",
                "https://api.github.com/repos/contributor2/project/actions/runs?per_page=100&branch=main",
            ],
        ),
        (
            ["."],
            {"GITHUB_API_URL": "https://theapi.nedhub.com"},
            [
                "https://theapi.nedhub.com/repos/owner/repo/actions/runs?per_page=100&branch=mainbranch",
            ],
        ),
        (
            ["https://github.com/me/myproject.git", "mybranch"],
            {},
            [
                "https://api.github.com/repos/me/myproject/actions/runs?per_page=100&branch=mybranch",
            ],
        ),
        (
            ["dir-enterprise"],
            {
                "GITHUB_SERVER_URL": "https://mygithub.enterprise.com",
                "GITHUB_API_URL": "https://api.mygithub.enterprise.com",
            },
            [
                "https://api.mygithub.enterprise.com/repos/me/myproject/actions/runs?per_page=100&branch=master",
            ],
        ),
        (
            ["dir-bug22"],
            {
                "GITHUB_SERVER_URL": "git@git.mydomain.com",
                "GITHUB_API_URL": "https://githubapi.mydomain.com",
            },
            [
                "https://githubapi.mydomain.com/repos/davidszotten/davidrepo/actions/runs?per_page=100&branch=master",
            ],
        ),
    ],
)
def test_gha_urls(monkeypatch, mocked_gha_urls_dependencies, args, evars, urls):
    for name, value in evars.items():
        monkeypatch.setenv(name, value)
    assert gha_urls(*args) == urls


@pytest.mark.parametrize(
    "args, evars, msg",
    [
        (
            ["https://mygithub.com/me/myproject.git"],
            {},
            "Branch is required for URL repo",
        ),
        (
            ["what!?"],
            {},
            "Don't understand repo 'what!?'",
        ),
        (
            ["dir-only-gitlab"],
            {},
            "Couldn't find GitHub repo from remote URLs: \n['https://gitlab.com/maintainer/project.git']",
        ),
    ],
)
def test_gha_urls_fails(
    capsys, monkeypatch, mocked_gha_urls_dependencies, args, evars, msg
):
    with pytest.raises(SystemExit):
        gha_urls(*args)
    assert capsys.readouterr().err.strip() == msg
