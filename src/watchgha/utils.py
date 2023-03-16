import datetime
import itertools
import json
import os
import time

import requests


def nice_time(dt):
    dt = dt.astimezone()
    now = datetime.datetime.now()
    if dt.date() != now.date():
        if dt.year != now.year:
            fmt = "%Y-%m-%d %I:%M%p"
        else:
            fmt = "%m-%d %I:%M%p"
    else:
        fmt = "%I:%M%p"
    return dt.strftime(fmt).lower()


def to_datetime(isostr):
    # 3.11 accepts Z, but older Pythons don't.
    isostr = isostr.replace("Z", "+00:00")
    return datetime.datetime.fromisoformat(isostr)


class DictAttr:
    def __init__(self, d):
        self.d = d

    def __getattr__(self, name):
        return self.d[name]


class Http:
    """
    Helper for getting JSON from URLs.

    Uses the GITHUB_TOKEN environment variable (if set) as authentication.

    Define SAVE_JSON=1 in the environment to save retrieved data in .json files.

    """

    RETRY_STATUS_CODES = {502}

    def __init__(self):
        self.count = itertools.count()

    def get_json(self, url):
        headers = {}
        token = os.environ.get("GITHUB_TOKEN", "")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        for _ in range(3):
            resp = requests.get(url, headers=headers)
            if resp.status_code not in self.RETRY_STATUS_CODES:
                break
            time.sleep(0.5)
        resp.raise_for_status()

        data = resp.json()
        if int(os.environ.get("SAVE_JSON", "0")):
            filename = f"get_{next(self.count):03d}.json"
            with open("get_index.txt", "a") as index:
                print(f"{filename}: {url}", file=index)
            with open(filename, "w") as jout:
                json.dump(data, jout, indent=4)
        return data


get_json = Http().get_json
