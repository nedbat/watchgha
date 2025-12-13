"""Data collection and rendering for watchgha."""

import datetime
import itertools
import json
import re
from dataclasses import dataclass

import trio

from .bucketer import DatetimeBucketer
from .utils import human_key, nice_time, to_datetime, DictAttr


bucketer = DatetimeBucketer(5)

CSTYLES = {
    "failure": "red bold",
    "pending": "dim",
    "queued": "dim",
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
    "skipped": "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}",
    "startup_failure": "\N{BALLOT X}",
    "success": "\N{CHECK MARK}",
    "waiting": "\N{OCTAGONAL SIGN}",
}

STEPDOTS = {
    "cancelled": "[red]\N{DAGGER}[/]",
    "failure": "[red]\N{BULLET}[/]",
    "in_progress": "[white]\N{BULLET}[/]",
    "pending": "[dim white]\N{BULLET}[/]",
    "queued": "[dim white]\N{BULLET}[/]",
    "skipped": "[default]\N{WHITE BULLET}[/]",
    "success": "[green]\N{BULLET}[/]",
}

# Conclusion states to mark as bad.
CONCLUSION_BAD = {
    "failure",
    "startup_failure",
    "cancelled",
}

def summary_style_icon(data):
    summary = data["status"]
    if summary == "completed":
        summary = data["conclusion"]
    style = CSTYLES.get(summary, "default")
    icon = CICONS.get(summary, " ")
    return summary, style, icon


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


def job_sort_key(job_data):
    return (
        bucketer.defuzz(job_data["created_dt"]),
        human_key(job_data["name"]),
    )


@dataclass
class Status:
    done: bool = False
    succeeded: bool = False
    total: int = 0
    num_succeeded: int = 0
    num_failed: int = 0


def draw_runs(urls, datafn, outfn, only_words=None):
    # Workflow runs is a flat list of runs.  We bucket them by time started,
    # sha, and event to create "events".  Each event has a number of runs, each
    # run has a number of jobs, each job has a number of steps. They end up
    # displayed as:
    #
    #   event-name sha, time
    #       outcome run-name, url
    #           job-name     current-step-or-outcome

    events = trio.run(get_events, urls, datafn, only_words)

    def safe_outfn(s):
        """Scrub control characters from lines of output."""
        outfn(re.sub(r"[\x00-\x1f\x7f-\x9f]", "", s))

    status = Status()
    for runs in events:
        for run in runs:
            for job in run["jobs"]:
                status.total += 1
                if job["status"] == "completed":
                    if job["conclusion"] in CONCLUSION_BAD:
                        status.num_failed += 1
                    else:
                        status.num_succeeded += 1

    status.done, status.succeeded = draw_events(events, safe_outfn)
    return status


async def get_events(urls, datafn, only_words):
    runs = []

    async def runs_from_url(url):
        runs.extend(json.loads(await datafn(url))["workflow_runs"])

    async with trio.open_nursery() as nursery:
        for url in urls:
            nursery.start_soon(runs_from_url, url)

    # In odd situations (duplicate remotes) we can get the same run more than
    # once. De-duplicate them.
    runs_by_id = {r["id"]: r for r in runs}
    runs = list(runs_by_id.values())

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

            if only_words is not None:
                event_runs = [
                    run
                    for run in event_runs
                    if any(word in run["name"].lower() for word in only_words)
                ]
                if not event_runs:
                    continue

            events.append(event_runs)
            run_names_seen.update(these_runs_names)

            async def load_run(run):
                jobs = json.loads(await datafn(run["jobs_url"] + "?per_page=100"))["jobs"]
                for job in jobs:
                    job["created_dt"] = to_datetime(job["created_at"])
                run["jobs"] = sorted(jobs, key=job_sort_key)

            for run in event_runs:
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
                                    stepdots += STEPDOTS.get(ssum, "?")
                                current_step = f" {step['name']}"
                                break
                        else:
                            if steps:
                                current_step = steps[-1]["name"]
                            elif (
                                job["status"] == "completed"
                                and job["conclusion"] == "skipped"
                            ):
                                current_step = "skipped"

                j = DictAttr(job)
                outfn(
                    "      "
                    + f"{j.name:30} [{style}]{icon}[/] "
                    + f"{stepdots}[{style}]{current_step}[/]"
                )

    return done, succeeded
