"""
Helper for getting data from URLs.
"""

import itertools
import mimetypes
import os

import httpx
import trio

from .utils import WatchGhaError


RETRY_STATUS_CODES = {502}


class Http:
    """
    Helper for getting data from URLs.

    Uses the GITHUB_TOKEN environment variable (if set) as authentication.

    Define SAVE_DATA=1 in the environment to save retrieved data in get_*.*
    files.

    """

    def __init__(self):
        # $set_env.py: SAVE_DATA - save all fetched data to get_* files.
        self.save = bool(int(os.environ.get("SAVE_DATA", "0")))
        if self.save:
            with open("get_index.txt", "w") as index:
                index.write("# URLs fetched:\n")
            self.count = itertools.count()
        self.auth = None
        self.headers = {}
        token = os.environ.get("GITHUB_TOKEN", "")
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        else:
            try:
                self.auth = httpx.NetRCAuth()
            except FileNotFoundError:
                self.auth = None

    async def get_data(self, url):
        async with httpx.AsyncClient(auth=self.auth) as client:
            resp = None
            try:
                for ntry in range(3):
                    resp = await client.get(
                        url,
                        headers=self.headers,
                        timeout=30,
                        follow_redirects=True,
                    )
                    if resp.status_code not in RETRY_STATUS_CODES:
                        break
                    await trio.sleep(0.05 * 2**ntry)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                # Some error messages have the URL, and some don't.  Add it in
                # if it isn't there already.
                if len(url) > 10 and url in str(e):
                    msg = str(e)
                else:
                    msg = f"Couldn't get {url!r}: {e}"
                if resp is not None:
                    try:
                        for label, text in resp.json().items():
                            msg += f"\n{label}: {text}"
                    except Exception:
                        msg += f"\n{resp.text}"
                raise WatchGhaError(msg) from e
            data = resp.text
            if self.save:
                ext = extension_for_content(resp)
                filename = f"get_{next(self.count):03d}{ext}"
                async with await trio.open_file("get_index.txt", "a") as index:
                    await index.write(f"{filename}: {url}\n")
                async with await trio.open_file(filename, "w") as out:
                    await out.write(data)
            return data


def extension_for_content(response):
    content_type = response.headers["content-type"].partition(";")[0].strip()
    return mimetypes.guess_extension(content_type)


_get_data = Http().get_data


async def get_data(*args, **kwargs):
    """Run get_data three times, with retry."""
    # I don't like that this has a retry loop and get_data above also does.
    for ntry in range(3):
        try:
            return await _get_data(*args, **kwargs)
        except Exception as exc:
            exc_to_raise = exc
            await trio.sleep(0.05 * 2**ntry)
    raise exc_to_raise
