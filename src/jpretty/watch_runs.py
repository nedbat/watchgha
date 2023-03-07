import datetime
import itertools
import json
import os

import requests
from rich.console import Console

from .bucketer import DatetimeBucketer
from .utils import nice_time, DictAttr


REPO = "nedbat/coveragepy"
BRANCH = "nedbat/test"

URL = f"https://api.github.com/repos/{REPO}/actions/runs?per_page=20&branch={BRANCH}"

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

def main():
    runs = http.get_json(URL)
    runs = runs["workflow_runs"]

    for run in runs:
        run["started_dt"] = datetime.datetime.fromisoformat(run["run_started_at"])

    runs.sort(key=run_sort_key, reverse=True)
    run_names_seen = set()

    for _, g in itertools.groupby(runs, key=run_group_key):
        these_runs = list(g)
        these_runs_names = set(r["name"] for r in these_runs)
        if not (these_runs_names - run_names_seen):
            continue
        _ = DictAttr(these_runs[0])
        console.print(
            f"[white bold]{_.display_title}[/] " +
            f"{_.head_branch} " +
            f"\\[{_.event}] " +
            f"  [dim]{_.head_sha:.12}  @{nice_time(_.started_dt)}[/]"
        )
        for r in these_runs:
            _ = DictAttr(r)
            cstyles = {
                "success": "green bold",
                "failure": "red bold",
            }
            console.print(
                f"   " +
                f"{_.status:12} " +
                f"[{cstyles.get(_.conclusion, 'default')}]{_.conclusion or '':10}[/] " +
                f"{_.name:20} " +
                f"  [blue link={_.html_url}]view {_.url.split('/')[-1]}[/]"
            )

            jobs = http.get_json(r["jobs_url"])["jobs"]
            for j in jobs:
                current_step = "---"
                style = "default"
                if j["status"] == "queued":
                    current_step = "queued"
                else:
                    steps = j["steps"]
                    for i, step in enumerate(steps):
                        if step["status"] == "completed" and step["conclusion"] == "failure":
                            current_step = f"{i+1}/{len(steps)}: {step['name']}"
                            style = cstyles["failure"]
                            break
                        if step["status"] == "in_progress":
                            current_step = f"{i+1}/{len(steps)}: {step['name']}"
                            break
                    else:
                        current_step = steps[-1]["name"]
                        style = cstyles["success"]

                _ = DictAttr(j)
                console.print(f"      {_.name:30} [{style}]{current_step}[/]")

        run_names_seen.update(these_runs_names)


if __name__ == "__main__":
    main()
