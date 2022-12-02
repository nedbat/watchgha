import datetime
import itertools
import json
import sys


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

def run_group_key(run_data):
    return (
        bucketer.defuzz(run_data["startedAt"]),
        run_data["headSha"],
        run_data["event"],
    )

def run_sort_key(run_data):
    return (
        run_data["startedAt"],
        run_data["headSha"],
        run_data["event"],
        run_data["workflowName"],
    )

def main():
    runs = json.load(sys.stdin)
    for run in runs:
        run["startedAt"] = datetime.datetime.fromisoformat(run["startedAt"])

    runs.sort(key=run_sort_key, reverse=True)
    for k, g in itertools.groupby(runs, key=run_group_key):
        runs = list(g)
        r0 = runs[0]
        print(r0["event"], r0["displayTitle"], r0["headBranch"], r0["startedAt"])
        for r in runs:
            print("   ", r["status"], r["conclusion"], r["url"])


if __name__ == "__main__":
    main()
