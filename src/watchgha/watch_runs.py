"""
Use the GitHub API to show the status of current GitHub Action runs on a
specific branch.

It tries to show enough runs to see the latest status of each workflow.  Runs
older than a week are not considered.

"""

import datetime
import itertools
import json
import re
import sys
import time
import urllib.parse

import click
import exceptiongroup
import rich.console
import trio

from .bucketer import DatetimeBucketer
from .utils import get_data, nice_time, to_datetime, DictAttr, WatchGhaError


bucketer = DatetimeBucketer(5)
console = rich.console.Console(highlight=False)


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
    "success": "green bold",
    "failure": "red bold",
    "startup_failure": "red bold",
}

# States that are finished.
FINISHED = {
    "success",
    "failure",
    "cancelled",
    "startup_failure",
}

CICONS = {
    "pending": "\N{TIMER CLOCK}",
    "queued": "\N{TIMER CLOCK}",
    "in_progress": "\N{CLOCKWISE OPEN CIRCLE ARROW}",
    "success": "\N{CHECK MARK}",
    "failure": "\N{BALLOT X}",
    "cancelled": "\N{DAGGER}",
    "startup_failure": "\N{BALLOT X}",
}

STEPDOTS = {
    "success": "[green]\N{BULLET}[/]",
    "failure": "[red]\N{BULLET}[/]",
    "skipped": "[default]\N{WHITE BULLET}[/]",
    "in_progress": "[white]\N{BULLET}[/]",
    "queued": "[dim white]\N{BULLET}[/]",
}


def summary_style_icon(data):
    summary = data["status"]
    if summary == "completed":
        summary = data["conclusion"]
    style = CSTYLES.get(summary, "default")
    icon = CICONS.get(summary, " ")
    return summary, style, icon


@click.command()
@click.option("--sha", help="The commit SHA to use. Must be a full SHA.")
@click.argument("repo_url")
@click.argument("branch_name", required=False)
def main(sha, repo_url, branch_name):
    # repo_url = "https://github.com/owner/repo.git"
    # repo_url = "git@github.com:someorg/somerepo.git"
    repo_match = re.fullmatch(
        r"(?:https://github.com/|git@github.com:)([^/]+/[^/]+?)(?:\.git|/)?", repo_url
    )
    if repo_match is None:
        raise Exception(f"Couldn't find GitHub repo from {repo_url!r}")

    url = f"https://api.github.com/repos/{repo_match[1]}/actions/runs"
    params = {"per_page": "40"}

    if branch_name:
        params["branch"] = branch_name
    elif sha:
        params["head_sha"] = sha

    url += "?" + urllib.parse.urlencode(params)

    output = ""
    done = False
    succeeded = False

    def doit():
        nonlocal output, done, succeeded
        with console.capture() as capture:
            done, succeeded = draw_runs(url, get_data, console.print)
        output = capture.get()

    watch_gha_errors = []

    def handle_watchghaerror(excgroup):
        watch_gha_errors.extend(excgroup.exceptions)

    def handle_keyboardinterrupt(excgroup):
        print("** interrupted **")

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
                    time.sleep(1)
                    doit()

    if watch_gha_errors:
        orig = watch_gha_errors[0].args[0]
        msg = f"Error: {orig.__class__.__name__}"
        if str(orig):
            msg += f": {orig}"
        print(msg)
        sys.exit(2)

    print(output, end="")
    sys.exit(0 if succeeded else 1)


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
            these_runs_names = set(run["name"] for run in event_runs)
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
            outfn(
                f"   "
                + f"[{style}]{icon} {summary:12}[/] "
                + f"[white bold]{r.name:16}[/] "
                + f"  [blue link={r.html_url}]view {r.html_url.split('/')[-1]}[/]"
            )

            if summary == "success":
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
                    f"      "
                    + f"{j.name:30} [{style}]{icon}[/] "
                    + f"{stepdots}[{style}]{current_step}[/]"
                )

    return done, succeeded
