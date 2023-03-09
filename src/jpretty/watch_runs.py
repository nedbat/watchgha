import datetime
import itertools
import json
import os
import re
import sys
import time

import requests
from rich.console import Console

from .bucketer import DatetimeBucketer
from .utils import nice_time, DictAttr


bucketer = DatetimeBucketer(5)
console = Console(highlight=False)


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


SAVE_JSON = int(os.environ.get("SAVE_JSON", "0"))


class Http:
    def __init__(self):
        self.count = itertools.count()

    def get_json(self, url):
        resp = requests.get(url)
        data = resp.json()
        if SAVE_JSON:
            with open(f"get_{next(self.count):03d}.json", "w") as jout:
                json.dump(data, jout, indent=4)
        return data


http = Http()


CSTYLES = {
    "success": "green bold",
    "failure": "red bold",
}

CICONS = {
    "pending": "\N{TIMER CLOCK}",
    "queued": "\N{TIMER CLOCK}",
    "in_progress": "\N{CLOCKWISE OPEN CIRCLE ARROW}",
    "success": "\N{CHECK MARK}",
    "failure": "\N{BALLOT X}",
    "cancelled": "\N{DAGGER}",
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


def main():
    repo_url, branch_name = sys.argv[1:]
    # repo_url = "https://github.com/nedbat/coveragepy.git"
    m = re.fullmatch(r"https://github.com/([^/]+/[^/]+)\.git", repo_url)

    url = f"https://api.github.com/repos/{m[1]}/actions/runs?per_page=20&branch={branch_name}"

    output = ""
    done = False

    def doit():
        nonlocal output, done
        with console.capture() as capture:
            done = draw_runs(url)
        output = capture.get()

    try:
        doit()
        if not done:
            with console.screen() as screen:
                while not done:
                    screen.update(output)
                    time.sleep(1)
                    doit()
    except KeyboardInterrupt:
        pass
    print(output)


def draw_runs(url):
    runs = http.get_json(url)
    runs = runs["workflow_runs"]

    for run in runs:
        run["started_dt"] = datetime.datetime.fromisoformat(run["run_started_at"])

    runs.sort(key=run_sort_key, reverse=True)
    run_names_seen = {"Cancel"}

    done = True
    for _, g in itertools.groupby(runs, key=run_group_key):
        these_runs = list(g)
        these_runs_names = set(r["name"] for r in these_runs)
        if not (these_runs_names - run_names_seen):
            continue
        days_old = (
            datetime.datetime.now(datetime.timezone.utc) - these_runs[0]["started_dt"]
        ).days
        if days_old > 7:
            continue
        _ = DictAttr(these_runs[0])
        console.print(
            f"[white bold]{_.display_title}[/] "
            + f"{_.head_branch} "
            + f"\\[{_.event}] "
            + f"  [dim]{_.head_sha:.12}  @{nice_time(_.started_dt)}[/]"
        )
        for r in these_runs:
            _ = DictAttr(r)
            summary, style, icon = summary_style_icon(r)
            if summary not in ["success", "failure", "cancelled"]:
                done = False
            console.print(
                f"   "
                + f"[{style}]{icon} {summary:12}[/] "
                + f"[white bold]{_.name:16}[/] "
                + f"  [blue link={_.html_url}]view {_.html_url.split('/')[-1]}[/]"
            )

            if summary != "success":
                jobs = http.get_json(r["jobs_url"])["jobs"]
                for j in jobs:
                    current_step, style, icon = summary_style_icon(j)
                    stepdots = ""
                    if current_step != "success":
                        if j["status"] == "queued":
                            current_step = "queued"
                            done = False
                        else:
                            steps = j["steps"]
                            for step in steps:
                                if (
                                    step["status"] == "completed"
                                    and step["conclusion"] == "failure"
                                ):
                                    current_step = f" {step['name']}"
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
                                current_step = steps[-1]["name"]

                    _ = DictAttr(j)
                    console.print(
                        f"      "
                        + f"{_.name:30} [{style}]{icon}[/] "
                        + f"{stepdots}[{style}]{current_step}[/]"
                    )

        run_names_seen.update(these_runs_names)

    return done
