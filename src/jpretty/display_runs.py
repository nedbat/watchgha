import datetime
import itertools
import json
import sys

from rich.console import Console

class DatetimeBucketer:
    def __init__(self, window):
        self.window = window
        # The set of good instants
        self.instants = set()
        # Map rounded times to good instants
        self.rounds = {}

    def roundings(self, dt):
        for jitter in [0, self.window / 2]:
            yield round((dt.timestamp() + jitter) / self.window)

    def defuzz(self, dt):
        if dt in self.instants:
            return dt

        for rounded in self.roundings(dt):
            instant = self.rounds.get(rounded)
            if instant is not None:
                return instant

        self.instants.add(dt)
        for rounded in self.roundings(dt):
            self.rounds[rounded] = dt

        return dt

bucketer = DatetimeBucketer(5)
console = Console(highlight=False)

def run_group_key(run_data):
    return (
        bucketer.defuzz(run_data["startedAt"]),
        run_data["headSha"],
        run_data["event"],
    )

def run_sort_key(run_data):
    return (
        bucketer.defuzz(run_data["startedAt"]),
        run_data["headSha"],
        run_data["event"],
        run_data["workflowName"],
    )

class DictAttr:
    def __init__(self, d):
        self.d = d

    def __getattr__(self, name):
        return self.d[name]

def main():
    runs = json.load(sys.stdin)
    for run in runs:
        run["startedAt"] = datetime.datetime.fromisoformat(run["startedAt"])

    runs.sort(key=run_sort_key, reverse=True)
    for k, g in itertools.groupby(runs, key=run_group_key):
        runs = list(g)
        _ = DictAttr(runs[0])
        console.print(
            f"[white b]{_.displayTitle}[/] " +
            f"{_.headBranch} " +
            f"\\[{_.event}] " +
            f"  [dim]{_.startedAt}[/]"
        )
        for r in runs:
            _ = DictAttr(r)
            cstyles = {
                "success": "green bold",
                "failure": "red bold",
            }
            console.print(
                f"   " +
                f"{_.status} " +
                f"[{cstyles.get(_.conclusion, 'default')}]{_.conclusion:10}[/] " +
                f"{_.workflowName:20} " +
                f"  [blue link={_.url}]view[/]"
            )


if __name__ == "__main__":
    main()
