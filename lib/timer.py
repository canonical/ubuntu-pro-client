"""
Timer script used to run all jobs that need to be frequently run on the system
"""

import logging

from datetime import datetime, timedelta

import collections
from typing import Any, Callable, Dict  # noqa: F401

from uaclient.cli import setup_logging
from uaclient.config import UAConfig
from uaclient.jobs.update_messaging import update_apt_and_motd_messages
from uaclient.jobs.update_state import update_status


LOG = logging.getLogger(__name__)
UPDATE_MESSAGING_INTERVAL = 21600  # 6 hours
UPDATE_STATUS_INTERVAL = 43200  # 12 hours

# Store the default run_interval_seconds for each job in this dict.
# OrderedDict is used to ensure each job is run sequentially in the order
# listed as some jobs may depend on completion of the previous job.
UACLIENT_JOBS = collections.OrderedDict(
    [
        (
            "update_messaging",
            {
                "job_func": update_apt_and_motd_messages,
                "run_interval_seconds": UPDATE_MESSAGING_INTERVAL,
            },
        ),
        (
            "update_status",
            {
                "job_func": update_status,
                "run_interval_seconds": UPDATE_STATUS_INTERVAL,
            },
        ),
    ]
)  # type: Dict[str, Dict[str, Any]]


def run_job(
    job_name: str, job_func: "Callable[[UAConfig], None]", cfg: UAConfig
) -> bool:
    """Run a job in a failsafe manner, returning True on success.

    :param job_name: Name of the job to run
    :param job_func: Job callable to call
    :param cfg: UAConfig instance

    :return: A bool True when successfully run. False if ignored or in error.
    """
    LOG.debug("Running job: %s", job_name)
    try:
        job_func(cfg)
    except Exception as e:
        LOG.warning("Error executing job %s: %s", job_name, str(e))
        return False

    return True


def run_jobs(cfg: UAConfig, current_time: datetime):
    """Run ordered UACLIENT_JOBS when next_run is before utcnow.

    Persist jobs-status with calculated next_run values to aid in timer state
    introspection for jobs which ave not yet run.
    """
    LOG.debug("Trigger UA Timer jobs")
    jobs_status = cfg.read_cache("jobs-status") or {}
    for job_name, job_info in UACLIENT_JOBS.items():
        if job_name in jobs_status:
            next_run = datetime.strptime(
                jobs_status[job_name]["next_run"], "%Y-%m-%dT%H:%M:%S.%f"
            )
            if next_run > current_time:
                continue  # Skip job as expected next_run hasn't yet passed
        job_func = job_info["job_func"]  # type: Callable[[UAConfig], None]
        if run_job(job_name=job_name, job_func=job_func, cfg=cfg):
            # Persist last_run and next_run UTC-based times on job success.
            jobs_status[job_name] = {
                "last_run": current_time,
                "next_run": current_time
                + timedelta(seconds=job_info["run_interval_seconds"]),
            }
    cfg.write_cache(key="jobs-status", content=jobs_status)


if __name__ == "__main__":
    cfg = UAConfig()
    current_time = datetime.utcnow()
    setup_logging(logging.INFO, logging.DEBUG)
    run_jobs(cfg=cfg, current_time=current_time)
