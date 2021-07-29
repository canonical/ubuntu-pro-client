"""
Timer script used to run all jobs that need to be frequently run on the system
"""

import json
import logging

import datetime

from collections import OrderedDict
from typing import Any, Callable, Dict  # noqa: F401

from uaclient.config import UAConfig
from uaclient import util
from uaclient.jobs.update_messaging import update_apt_and_motd_messages


LOG = logging.getLogger(__name__)

# We are currently storing the time frequency for each job at this dict,
# but we should move it later into uaclient.conf
uaclient_jobs = OrderedDict(
    {
        "update_messaging": {
            "job_func": update_apt_and_motd_messages,
            "run_interval_seconds": 14400,
        },
        "update_status": {
            "job_func": lambda cfg: None,
            "run_interval_seconds": 14400,
        },
    }
)


def run_job(
    job_name: str,
    job_func: "Callable[[UAConfig], None]",
    current_time: datetime.datetime,
    run_interval_seconds: int,
    jobs_status: "Dict[str, Any]",
    cfg: UAConfig,
) -> "Dict[str, Any]":
    """Run a job based on time constraints.

    If the current time is higher than the last time
    the job has successfully executed plus the expected
    time interval between job runs, we need to execute this
    job again.

    :param job_name: Name of the job to run.
    :param job_func: Job function to run
    :param run_interval_seconds: Interval in seconds that the job needs to
                                 wait before running again.
    :param jobs_status: A dict containing information about the last
                        successful run of all jobs that should run
                        in the system.

    :return: A dict containing the update last successful run of the job
             and the time it should execute next
    """
    seconds_to_add = datetime.timedelta(seconds=run_interval_seconds)
    if job_name in jobs_status:
        next_run = jobs_status[job_name]["next_run"]

        if current_time < next_run:
            return {}

    try:
        LOG.debug("Running job: %s", job_name)
        job_func(cfg)
    except Exception as e:
        LOG.warning("Error executing job: %s\n%s", job_name, str(e))
        return {}

    return {
        job_name: {
            "last_run": current_time,
            "next_run": current_time + seconds_to_add,
        }
    }


def main():
    cfg = UAConfig()
    jobs_status = cfg.read_cache("jobs-status") or {}
    current_time = datetime.datetime.now().replace(microsecond=0)

    for job_name, job_info in uaclient_jobs.items():
        job_func = job_info["job_func"]
        run_interval_seconds = job_info["run_interval_seconds"]

        # If the job fails run of should not run when this script
        # is executed, we will return an empty dict here, meaning
        # that no update will be made to the jobs_status dict
        jobs_status.update(
            run_job(
                job_name=job_name,
                job_func=job_func,
                current_time=current_time,
                run_interval_seconds=run_interval_seconds,
                jobs_status=jobs_status,
                cfg=cfg,
            )
        )

    cfg.write_cache(
        key="jobs-status",
        content=json.dumps(jobs_status, cls=util.DatetimeAwareJSONEncoder),
    )


if __name__ == "__main__":
    main()
