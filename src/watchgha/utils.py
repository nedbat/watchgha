import datetime
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
