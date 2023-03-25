import datetime
import itertools
import mimetypes
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
    Helper for getting data from URLs.

    Uses the GITHUB_TOKEN environment variable (if set) as authentication.

    Define SAVE_DATA=1 in the environment to save retrieved data in get_*.* files.

    """

    RETRY_STATUS_CODES = {502}

    def __init__(self):
        self.count = itertools.count()

    def get_data(self, url):
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
        data = resp.text
        if int(os.environ.get("SAVE_DATA", "0")):
            ext = extension_for_content(resp)
            filename = f"get_{next(self.count):03d}{ext}"
            with open("get_index.txt", "a") as index:
                print(f"{filename}: {url}", file=index)
            with open(filename, "w") as out:
                out.write(data)
        return data


def extension_for_content(response):
    content_type = response.headers['content-type'].partition(';')[0].strip()
    return mimetypes.guess_extension(content_type)


get_data = Http().get_data
