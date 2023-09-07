"""A module to show styling.

Run from the command line with:

    $ python3 -m watchgha.demo

"""

import json

import rich.console

from .data_core import FINISHED, draw_runs


RUN_COMMON = {
    "display_title": "fix: most awesome fix",
    "head_branch": "nedbat/test",
    "html_url": "https://github.com/owner/repo/actions/runs/123456789",
    "event": "push",
    "head_sha": "4b2ff58124791953563fdb52e40d9ab79d274d9a",
    "run_started_at": "2023-07-02T13:49:27Z",
}

DEMO_DATA = {
    "demo:one": {
        "workflow_runs": [
            {
                **RUN_COMMON,
                "name": "Test suite",
                "status": "in_progress",
                "jobs_url": "demo:jobs_tests",
            },
            *[
                {
                    **RUN_COMMON,
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
                "name": "Just one job",
                "status": "queued",
            },
        ],
    },
    "demo:jobs_tests": {
        "jobs": [
            {
                "name": "A delayed job",
                "status": "queued",
            },
            {
                "name": "A finished job",
                "status": "completed",
                "conclusion": "success",
            },
            {
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
    return json.dumps(DEMO_DATA[url])


def demo():
    console = rich.console.Console(highlight=False)
    draw_runs("demo:one", datafn=demo_datafn, outfn=console.print)


if __name__ == "__main__":
    demo()
