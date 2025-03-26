from __future__ import annotations

import datetime
import re
import time


class WatchGhaError(Exception):
    pass


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


class Interval:
    """Wait for an interval of time to pass.

    Better than time.sleep because it accounts for time spent doing things
    other than sleeping.

    """

    def __init__(self, secs):
        self.secs = secs
        self.last_time = time.time()

    def wait(self):
        now = time.time()
        delay = self.secs - (now - self.last_time)
        self.last_time = now
        if delay > 0:
            time.sleep(delay)


def human_key(s):
    """Turn a string into a sortable value that works how humans expect.

    "z23A" -> (["z", 23, "a"], "z23A")

    The original string is appended as a last value to ensure the
    key is unique enough so that "x1y" and "x001y" can be distinguished.
    """
    def tryint(s: str) -> str | int:
        """If `s` is a number, return an int, else `s` unchanged."""
        try:
            return int(s)
        except ValueError:
            return s

    return ([tryint(c) for c in re.split(r"(\d+)", s.casefold())], s)
