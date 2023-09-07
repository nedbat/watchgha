"""
Use the GitHub API to show the status of current GitHub Action runs on a
specific branch.

It tries to show enough runs to see the latest status of each workflow.  Runs
older than a week are not considered.

"""

import contextlib
import io
import os.path
import re
import signal
import sys
import urllib.parse

import click
import exceptiongroup
import rich.console

from .data_core import draw_runs
from .git_help import git_repo_url, git_branch
from .http_help import get_data
from .utils import Interval, WatchGhaError


console = rich.console.Console(highlight=False)
error_console = rich.console.Console(stderr=True, highlight=False)


def fatal(msg, status=2):
    error_console.print(msg)
    sys.exit(status)


@contextlib.contextmanager
def handle_resize(handler):
    original_sigwinch_handler = None
    try:
        # Save the original handler.
        original_sigwinch_handler = signal.getsignal(signal.SIGWINCH)
        # Call the given handler on sigwinch.
        signal.signal(signal.SIGWINCH, lambda _, __: handler())
    except AttributeError:
        # This system is probably windows, and doesn't have SIGWINCH.
        # Unfortunately there's no signal for window resize on windows and I
        # don't know how to properly handle it. Just swallow the error.
        pass

    # yield control to the with block, and re-raise any exceptions
    try:
        yield
    except:
        raise
    finally:
        # clean up our sigwinch handler if we set one
        if original_sigwinch_handler:
            signal.signal(signal.SIGWINCH, original_sigwinch_handler)


@click.command()
@click.option("--sha", help="The commit SHA to use. Must be a full SHA.")
@click.option(
    "--poll",
    help="How many seconds between refreshes.",
    type=int,
    default=15,
    show_default=True,
)
@click.option("--wait-for-start", is_flag=True, help="Wait for jobs to start")
@click.argument("repo", default=".")
@click.argument("branch", required=False)
def main(sha, poll, wait_for_start, repo, branch):
    """
    Watch GitHub Action runs.

    Repeatedly gets the latest status and redraws the screen, until all of the
    jobs are complete.

    REPO is a local directory or GitHub URL, defaulting to ".".

    BRANCH is defaulted from the git repo.

    """
    watcher = GhaWatcher(
        url=gha_url(repo, branch, sha),
        get_data=get_data,
    )

    watcher.watch(wait_for_start, poll, console)


def gha_url(repo, branch, sha):
    """Figure out the GHA api URL to use for `repo`, `branch`, and `sha`."""
    if os.path.isdir(repo):
        repo_url = git_repo_url(repo)
    elif ":" in repo:
        repo_url = repo
    else:
        fatal(f"Don't understand repo {repo!r}")

    # repo_url = "https://github.com/owner/repo.git"
    # repo_url = "git@github.com:someorg/somerepo.git"
    repo_match = re.fullmatch(
        r"(?:https://github.com/|git@github.com:)([^/]+/[^/]+?)(?:\.git|/)?",
        repo_url
    )
    if repo_match is None:
        fatal(f"Couldn't find GitHub repo from {repo_url!r}")

    url = f"https://api.github.com/repos/{repo_match[1]}/actions/runs"
    params = {"per_page": "40"}

    if sha:
        params["head_sha"] = sha
    elif branch:
        params["branch"] = branch
    else:
        params["branch"] = git_branch()

    url += "?" + urllib.parse.urlencode(params)
    return url


class GhaWatcher:
    def __init__(self, url, get_data):
        self.url = url
        self.get_data = get_data
        self.status = 0
        self.error = None

    def watch(self, wait_for_start, poll, console):
        self.done = False
        self.succeeded = False
        self.interrupted = False

        self.watch_gha_errors = []
        interval = Interval(poll)

        output = ""

        with exceptiongroup.catch(
            {
                WatchGhaError: self.handle_watchghaerror,
                KeyboardInterrupt: self.handle_keyboardinterrupt,
            }
        ):
            while True:
                output = self.get_gha_display()
                if wait_for_start:
                    if not self.done:
                        break
                else:
                    break

            if not self.done:
                with console.screen() as screen:
                    with handle_resize(lambda: screen.update(output)):
                        while not self.done:
                            screen.update(output)
                            interval.wait()
                            output = self.get_gha_display()

        if self.watch_gha_errors:
            fatal(self.watch_gha_errors[0])
        console.print(output, end="")
        if self.interrupted:
            fatal("** interrupted **", status=2)
        sys.exit(0 if self.succeeded else 1)

    def handle_watchghaerror(self, excgroup):
        self.watch_gha_errors.extend(excgroup.exceptions)

    def handle_keyboardinterrupt(self, excgroup):
        self.interrupted = True

    def get_gha_display(self):
        stream = io.StringIO()

        self.done, self.succeeded = draw_runs(
            self.url,
            datafn=self.get_data,
            outfn=lambda s: print(s, file=stream),
        )
        return stream.getvalue()
