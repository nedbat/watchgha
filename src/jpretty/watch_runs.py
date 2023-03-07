import datetime
import itertools

import requests
from rich.console import Console

from .bucketer import DatetimeBucketer
from .utils import nice_time, DictAttr


REPO = "nedbat/coveragepy"
BRANCH = "master"

URL = f"https://api.github.com/repos/{REPO}/actions/runs?per_page=50&branch={BRANCH}"

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

def main():
    runs = requests.get(URL).json()
    runs = runs["workflow_runs"]

    for run in runs:
        run["started_dt"] = datetime.datetime.fromisoformat(run["run_started_at"])

    runs.sort(key=run_sort_key, reverse=True)

    for i, (k, g) in enumerate(itertools.groupby(runs, key=run_group_key)):
        these_runs = list(g)
        if i == 1:
            console.print()
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
                f"[{cstyles.get(_.conclusion, 'default')}]{_.conclusion:10}[/] " +
                f"{_.name:20} " +
                f"  [blue link={_.url}]view {_.url.split('/')[-1]}[/]"
            )


if __name__ == "__main__":
    main()
