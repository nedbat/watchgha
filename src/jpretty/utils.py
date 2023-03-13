import datetime
import itertools
import os

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


class DictAttr:
    def __init__(self, d):
        self.d = d

    def __getattr__(self, name):
        return self.d[name]


class Http:
    """
    Helper for getting JSON from URLs.

    Define SAVE_JSON in the environment to save retrieved data in .json files.
    """

    def __init__(self):
        self.count = itertools.count()

    def get_json(self, url):
        resp = requests.get(url)
        data = resp.json()
        if int(os.environ.get("SAVE_JSON", "0")):
            filename = f"get_{next(self.count):03d}.json"
            with open("get_index.txt", "a") as index:
                print(f"{filename}: {url}", file=index)
            with open(filename, "w") as jout:
                json.dump(data, jout, indent=4)
        return data


get_json = Http().get_json
