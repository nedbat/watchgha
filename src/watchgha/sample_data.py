import datetime
import itertools
import json

from .data_core import FINISHED, draw_runs

next_id = itertools.count().__next__

NOW = datetime.datetime.now(datetime.timezone.utc).replace(hour=16, minute=55, second=30)

def next_isodatetime():
    # The sample data makes ~16 datetimes.  We want them all to be within 5
    # seconds, but not all within the same second.
    when = NOW - datetime.timedelta(milliseconds=next_id() * 100)
    return when.isoformat(timespec='seconds')

def run_common():
    return {
        "id": next_id(),
        "display_title": "fix: most awesome fix",
        "head_branch": "nedbat/test",
        "html_url": "https://github.com/owner/repo/actions/runs/123456789",
        "event": "push",
        "head_sha": "4b2ff58124791953563fdb52e40d9ab79d274d9a",
        "run_started_at": next_isodatetime(),
    }

def job_common():
    return {
        "id": next_id(),
        "created_at": next_isodatetime(),
    }

SAMPLE_DATA = {
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
            {
                **run_common(),
                "name": "Malicious \n\n\n\n data",
                "status": "in_progress",
                "jobs_url": "demo:jobs_malicious",
            },
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
    "demo:jobs_malicious": {
        "jobs": [
            {
                **job_common(),
                "name": "A \x1B[1mMALICIOUS\x1B[0m job",
                "status": "queued",
            },
        ],
    },
}


async def sample_datafn(url):
    url = url.partition("?")[0]
    return json.dumps(SAMPLE_DATA[url])


def sample(outfn):
    draw_runs(["demo:one"], datafn=sample_datafn, outfn=outfn)
