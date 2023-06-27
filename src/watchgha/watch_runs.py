"""
Use the GitHub API to show the status of current GitHub Action runs on a
specific branch.

It tries to show enough runs to see the latest status of each workflow.  Runs
older than a week are not considered.

"""

import datetime
import io
import itertools
import json
import os.path
import re
import sys
import time
import urllib.parse

import click
import exceptiongroup
import rich.console
import trio

from .bucketer import DatetimeBucketer
from .git_help import git_repo_url, git_branch
from .utils import get_data, nice_time, to_datetime, DictAttr, WatchGhaError


bucketer = DatetimeBucketer(5)
console = rich.console.Console(highlight=False)
error_console = rich.console.Console(stderr=True, highlight=False)


def run_group_key(run_data):
    return (
        bucketer.defuzz(run_data["started_dt"]),
        run_data["head_sha"],
        run_data["event"],
    )


def run_sort_key(run_data):
    return (
        bucketer.defuzz(run_data["started_dt"]),
        run_data["head_sha"],
        run_data["event"],
        run_data["name"],
    )


CSTYLES = {
    "failure": "red bold",
    "startup_failure": "red bold",
    "success": "green bold",
}

# States that are finished.
FINISHED = {
    "cancelled",
    "failure",
    "skipped",
    "startup_failure",
    "success",
}

# States that don't need jobs displayed.
NO_JOBS = {
    "skipped",
    "success",
}

CICONS = {
    "cancelled": "\N{DAGGER}",
    "failure": "\N{BALLOT X}",
    "in_progress": "\N{CLOCKWISE OPEN CIRCLE ARROW}",
    "pending": "\N{TIMER CLOCK}",
    "queued": "\N{TIMER CLOCK}",
    "skipped": "\N{BALLOT BOX}",
    "startup_failure": "\N{BALLOT X}",
    "success": "\N{CHECK MARK}",
}

STEPDOTS = {
    "failure": "[red]\N{BULLET}[/]",
    "in_progress": "[white]\N{BULLET}[/]",
    "queued": "[dim white]\N{BULLET}[/]",
    "skipped": "[default]\N{WHITE BULLET}[/]",
    "success": "[green]\N{BULLET}[/]",
}


def summary_style_icon(data):
    summary = data["status"]
    if summary == "completed":
        summary = data["conclusion"]
    style = CSTYLES.get(summary, "default")
    icon = CICONS.get(summary, " ")
    return summary, style, icon


def fatal(msg, status=2):
    error_console.print(msg)
    sys.exit(status)


@click.command()
@click.option("--sha", help="The commit SHA to use. Must be a full SHA.")
@click.option(
    "--poll",
    help="How many seconds between refreshes.",
    type=int,
    default=1,
    show_default=True,
)
@click.argument("repo", default=".")
@click.argument("branch", required=False)
def main(sha, poll, repo, branch):
    """
    Watch GitHub Action runs.

    Repeatedly gets the latest status and redraws the screen, until all of the
    jobs are complete.

    REPO is a local directory or GitHub URL, defaulting to ".".

    BRANCH is defaulted from the git repo.

    """
    url = gha_url(repo, branch, sha)

    output = ""
    done = False
    succeeded = False
    interrupted = False

    def doit():
        nonlocal output, done, succeeded
        stream = io.StringIO()
        done, succeeded = draw_runs(
            url,
            datafn=get_data,
            outfn=lambda s: print(s, file=stream),
        )
        output = stream.getvalue()

    watch_gha_errors = []

    def handle_watchghaerror(excgroup):
        watch_gha_errors.extend(excgroup.exceptions)

    def handle_keyboardinterrupt(excgroup):
        nonlocal interrupted
        interrupted = True

    with exceptiongroup.catch(
        {
            WatchGhaError: handle_watchghaerror,
            KeyboardInterrupt: handle_keyboardinterrupt,
        }
    ):
        doit()
        if not done:
            with console.screen() as screen:
                while not done:
                    screen.update(output)
                    time.sleep(poll)
                    doit()

    if watch_gha_errors:
        fatal(watch_gha_errors[0])

    console.print(output, end="")
    if interrupted:
        fatal("** interrupted **", status=2)
    sys.exit(0 if succeeded else 1)


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


def draw_runs(url, datafn, outfn):
    # Workflow runs is a flat list of runs.  We bucket them by time started,
    # sha, and event to create "events".  Each event has a number of runs, each
    # run has a number of jobs, each job has a number of steps. They end up
    # displayed as:
    #
    #   event-name sha, time
    #       outcome run-name, url
    #           job-name     current-step-or-outcome

    events = trio.run(get_events, url, datafn)
    done, succeeded = draw_events(events, outfn)
    return done, succeeded


async def get_events(url, datafn):
    runs = json.loads(await datafn(url))["workflow_runs"]

    async with trio.open_nursery() as nursery:
        for run in runs:
            run["started_dt"] = to_datetime(run["run_started_at"])

        runs.sort(key=run_sort_key, reverse=True)
        run_names_seen = {"Cancel"}

        events = []

        for _, g in itertools.groupby(runs, key=run_group_key):
            event_runs = list(g)
            these_runs_names = {run["name"] for run in event_runs}
            # If the .yml file couldn't even be parsed, the run name is the
            # name of the .yml file.  Exclude those, or a bad parse will
            # pollute the run list.
            these_runs_names = {
                n for n in these_runs_names if not n.startswith(".github/")
            }
            if not (these_runs_names - run_names_seen):
                continue
            days_old = (
                datetime.datetime.now(datetime.timezone.utc)
                - event_runs[0]["started_dt"]
            ).days
            if days_old > 7:
                continue

            events.append(event_runs)
            run_names_seen.update(these_runs_names)

            async def load_run(run):
                run["jobs"] = json.loads(await datafn(run["jobs_url"]))["jobs"]

            for run in event_runs:
                summary, _, _ = summary_style_icon(run)
                if summary != "success":
                    nursery.start_soon(load_run, run)

        return events


def draw_events(events, outfn):
    done = True
    succeeded = True
    for event_runs in events:
        e = DictAttr(event_runs[0])
        outfn(
            f"[white bold]{e.display_title}[/] "
            + f"{e.head_branch} "
            + f"\\[{e.event}] "
            + f"  [dim]{e.head_sha:.12}  @{nice_time(e.started_dt)}[/]"
        )
        for run in event_runs:
            summary, style, icon = summary_style_icon(run)
            if summary not in FINISHED:
                done = False
            r = DictAttr(run)
            run_id = r.html_url.split("/")[-1]
            outfn(
                "   "
                + f"[{style}]{icon} {summary:12}[/] "
                + f"[white bold]{r.name:16}[/] "
                + f"  [blue link={r.html_url}]view {run_id}[/]"
            )

            if summary in NO_JOBS:
                continue

            succeeded = False
            for job in run["jobs"]:
                current_step, style, icon = summary_style_icon(job)
                stepdots = ""
                if current_step != "success":
                    if job["status"] == "queued":
                        current_step = "queued"
                        done = False
                    else:
                        steps = job["steps"]
                        for step in steps:
                            if (
                                step["status"] == "completed"
                                and step["conclusion"] == "failure"
                            ):
                                current_step = f"failure {step['name']}"
                                break
                            if step["status"] == "in_progress":
                                done = False
                                stepdots = ""
                                for s in steps:
                                    ssum = summary_style_icon(s)[0]
                                    stepdots += STEPDOTS.get(ssum, ssum)
                                current_step = f" {step['name']}"
                                break
                        else:
                            if steps:
                                current_step = steps[-1]["name"]
                            else:
                                current_step = "-None-"

                j = DictAttr(job)
                outfn(
                    "      "
                    + f"{j.name:30} [{style}]{icon}[/] "
                    + f"{stepdots}[{style}]{current_step}[/]"
                )

    return done, succeeded
