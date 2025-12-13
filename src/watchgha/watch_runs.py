"""
Use the GitHub API to show the status of current GitHub Action runs on a
specific branch.

It tries to show enough runs to see the latest status of each workflow.  Runs
older than a week are not considered.

"""

import contextlib
import io
import os
import re
import signal
import sys
import urllib.parse

from os.path import isdir

import click
import exceptiongroup
import rich.console

from .data_core import Status, draw_runs
from .git_help import git_repo_urls, git_branch
from .http_help import get_data
from .utils import Interval, WatchGhaError


console = rich.console.Console(highlight=False)
error_console = rich.console.Console(stderr=True, highlight=False)


def fatal(msg, status=1):
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
@click.option(
    "--wait", "--wait-for-start", is_flag=True, help="Wait for jobs to start."
)
@click.option(
    "--only",
    help=(
        "Words to limit the workflows shown. "
        + "Only workflows with these comma separated case insensitive substrings "
        + "in their names will be shown."
    ),
)
@click.option("--message", help="A message to display at the top of the screen.")
@click.argument("repo", default=".")
@click.argument("branch", required=False)
def main(sha, poll, wait, only, message, repo, branch):
    """
    Watch GitHub Action runs.

    Repeatedly gets the latest status and redraws the screen, until all of the
    jobs are complete.

    REPO is a local directory or GitHub URL, defaulting to ".".

    BRANCH is defaulted from the git repo.

    """
    if only is not None:
        only_words = [w.strip() for w in only.split(",")]
    else:
        only_words = None

    watcher = GhaWatcher(
        urls=gha_urls(repo, branch, sha),
        get_data_fn=get_data,
        only_words=only_words,
        message=message,
    )

    watcher.watch(wait, poll, console)


def gha_urls(repo, branch=None, sha=None):
    """Figure out the GHA api URLs to use for `repo`, `branch`, and `sha`."""
    if isdir(repo):
        repo_urls = list(git_repo_urls(repo))
        if branch is None:
            branch = git_branch(repo)
    elif ":" in repo:
        repo_urls = [repo]
        if branch is None:
            fatal(f"Branch is required for URL repo")
    else:
        fatal(f"Don't understand repo {repo!r}")

    params = {"per_page": "100"}
    if sha:
        params["head_sha"] = sha
    else:
        assert branch is not None
        params["branch"] = branch
    url_args = urllib.parse.urlencode(params)

    github_urls = []
    for repo_url in repo_urls:
        # repo_url = "https://github.com/owner/repo.git"
        # repo_url = "git@github.com:someorg/somerepo.git"
        # see also https://docs.github.com/en/actions/learn-github-actions/variables#default-environment-variables
        server_url = os.getenv("GITHUB_SERVER_URL", "https://github.com")
        repo_match = re.fullmatch(
            rf"(?:{re.escape(server_url)}|git@github.com)[/:]?([^/]+/[^/]+?)(?:\.git|/)?",
            repo_url,
        )
        if repo_match is None:
            continue

        api_url = os.getenv("GITHUB_API_URL", "https://api.github.com")
        url = f"{api_url}/repos/{repo_match[1]}/actions/runs?{url_args}"
        github_urls.append(url)

    if not github_urls:
        fatal(f"Couldn't find GitHub repo from remote URLs: {repo_urls!r}")

    return github_urls


class GhaWatcher:
    def __init__(self, urls, get_data_fn, only_words, message):
        self.urls = urls
        self.get_data_fn = get_data_fn
        self.only_words = only_words
        self.message = message
        self.status = 0
        self.error = None

    def watch(self, wait_for_start, poll, console):
        self.status = Status()
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
                    if not self.status.done:
                        break
                else:
                    break

            if not self.status.done:
                with console.screen() as screen:
                    with handle_resize(lambda: screen.update(output)):
                        while not self.status.done:
                            screen.update(output)
                            self.update_terminal_progress()
                            interval.wait()
                            output = self.get_gha_display()

        self.clear_terminal_progress()

        if self.watch_gha_errors:
            fatal(self.watch_gha_errors[0])
        console.print(output, end="")
        if self.interrupted:
            fatal("** interrupted **", status=2)
        sys.exit(0 if self.status.succeeded else 1)

    def handle_watchghaerror(self, excgroup):
        self.watch_gha_errors.extend(excgroup.exceptions)

    def handle_keyboardinterrupt(self, excgroup):
        self.interrupted = True

    def get_gha_display(self):
        stream = io.StringIO()

        self.status = draw_runs(
            self.urls,
            datafn=self.get_data_fn,
            outfn=lambda s: print(s, file=stream),
            only_words=self.only_words,
        )
        output = stream.getvalue()
        if self.message:
            output = f"{self.message}\n{output}"
        return output

    def update_terminal_progress(self):
        finished = self.status.num_succeeded + self.status.num_failed
        percent_done = finished * 100 // self.status.total
        state = 2 if self.status.num_failed else 1
        osc_9_4(state, percent_done)

    def clear_terminal_progress(self):
        osc_9_4(0, 0)

def osc_9_4(st, pr):
    sys.stdout.write(f"\033]9;4;{st};{pr}\033\\")
    sys.stdout.flush()
