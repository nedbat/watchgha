"""A module to show styling.

Run from the command line with:

    $ python3 -m watchgha.demo

"""

import datetime
import itertools
import json

import rich.console

from .data_core import FINISHED, draw_runs


next_id = itertools.count().__next__

def run_common():
    return {
        "id": next_id(),
        "display_title": "fix: most awesome fix",
        "head_branch": "nedbat/test",
        "html_url": "https://github.com/owner/repo/actions/runs/123456789",
        "event": "push",
        "head_sha": "4b2ff58124791953563fdb52e40d9ab79d274d9a",
        "run_started_at": datetime.datetime.now().isoformat(timespec='seconds') + "Z"
    }

def job_common():
    return {
        "id": next_id(),
        "created_at": datetime.datetime.now().isoformat(timespec='seconds') + "Z"
    }

DEMO_DATA = {
    "demo:one": {
        "workflow_runs": [
            {
                **run_common(),
                "name": "Test suite",
                "status": "in_progress",
                "jobs_url": "demo:jobs_tests",
            },
            *[
                {
                    **run_common(),
                    "name": f"A {conc} run",
                    "status": "completed",
                    "conclusion": conc,
                    "jobs_url": "demo:jobs_1",
                }
                for conc in FINISHED
            ],
        ],
    },
    "demo:jobs_1": {
        "jobs": [
            {
                **job_common(),
                "name": "Just one job",
                "status": "queued",
            },
        ],
    },
    "demo:jobs_tests": {
        "jobs": [
            {
                **job_common(),
                "name": "A delayed job",
                "status": "queued",
            },
            {
                **job_common(),
                "name": "A finished job",
                "status": "completed",
                "conclusion": "success",
            },
            {
                **job_common(),
                "name": "A failed job",
                "status": "completed",
                "conclusion": "failure",
                "steps": [
                    {
                        "status": "completed",
                        "conclusion": "success",
                    },
                    {
                        "status": "completed",
                        "conclusion": "failure",
                        "name": "Didn't work",
                    },
                    {
                        "status": "queued",
                    },
                ],
            },
            *[
                {
                    **job_common(),
                    "name": f"Test suite Py 3.{py}",
                    "status": "in_progress",
                    "steps": [
                        *[
                            {
                                "status": "completed",
                                "conclusion": "success",
                            }
                            for _ in range(3 - py % 2)
                        ],
                        {
                            "status": "skipped",
                        },
                        {
                            "name": "Prep tests" if (py % 2) else "Run the tests",
                            "status": "in_progress",
                        },
                        *[
                            {
                                "status": "queued",
                            }
                            for _ in range(2 + py % 2)
                        ],
                    ],
                }
                for py in [8, 9, 10, 11]
            ],
        ],
    },
}


async def demo_datafn(url):
    url = url.partition("?")[0]
    return json.dumps(DEMO_DATA[url])


def demo():
    console = rich.console.Console(highlight=False)
    draw_runs(["demo:one"], datafn=demo_datafn, outfn=console.print)


if __name__ == "__main__":
    demo()
