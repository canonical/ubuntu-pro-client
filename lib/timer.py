"""
Timer used to run all jobs that need to be frequently run on the system
"""

import logging
from datetime import datetime, timedelta
from typing import Callable

from uaclient.cli import setup_logging
from uaclient.config import UAConfig
from uaclient.jobs.gcp_auto_attach import gcp_auto_attach
from uaclient.jobs.metering import metering_enabled_resources
from uaclient.jobs.update_messaging import update_apt_and_motd_messages
from uaclient.jobs.update_state import update_status

LOG = logging.getLogger(__name__)
UPDATE_MESSAGING_INTERVAL = 21600  # 6 hours
UPDATE_STATUS_INTERVAL = 43200  # 12 hours
METERING_INTERVAL = 0  # 4 hours in the future, disabled as of now


class TimedJob:
    def __init__(
        self,
        name: str,
        job_func: Callable[..., None],
        default_interval_seconds: int,
    ):
        self.name = name
        self._job_func = job_func
        self._default_interval_seconds = default_interval_seconds

    def run(self, cfg: UAConfig):
        """Run a job in a failsafe manner, returning True on success.
        Checks if the job is not disabled before running it.

        :param cfg: UAConfig instance

        :return: A bool True when successfully run. False if ignored
            or in error.
        """
        if not self._should_run(cfg):
            return False

        LOG.debug("Running job: %s", self.name)
        try:
            self._job_func(cfg=cfg)
        except Exception as e:
            LOG.warning("Error executing job %s: %s", self.name, str(e))
            return False

        return True

    def run_interval_seconds(self, cfg: UAConfig):
        """Return the run_interval for the job based on config or defaults."""
        configured_interval = getattr(cfg, "{}_timer".format(self.name), None)
        if configured_interval is None:
            debug_msg = (
                "No config set for {}, default value will be used."
            ).format(self.name)
            LOG.debug(debug_msg)
            return self._default_interval_seconds
        elif (
            not isinstance(configured_interval, int) or configured_interval < 0
        ):
            error_msg = (
                "Invalid value for {} interval found in config. "
                "Default value will be used."
            ).format(self.name)
            LOG.error(error_msg)
            return self._default_interval_seconds
        return configured_interval

    def _should_run(self, cfg):
        """Verify if the job has a valid (non-zero) interval."""
        return self.run_interval_seconds(cfg) != 0


UACLIENT_JOBS = [
    TimedJob(
        "update_messaging",
        update_apt_and_motd_messages,
        UPDATE_MESSAGING_INTERVAL,
    ),
    TimedJob("update_status", update_status, UPDATE_STATUS_INTERVAL),
    TimedJob("metering", metering_enabled_resources, METERING_INTERVAL),
]


def run_jobs(cfg: UAConfig, current_time: datetime):
    """Run jobs in order when next_run is before current_time.

    Persist jobs-status with calculated next_run values to aid in timer
    state introspection for jobs which have not yet run.
    """
    LOG.debug("Trigger UA Timer jobs")
    jobs_status = cfg.read_cache("jobs-status") or {}
    for job in UACLIENT_JOBS:
        if job.name in jobs_status:
            print(type(jobs_status[job.name]["next_run"]))
            next_run = datetime.strptime(
                jobs_status[job.name]["next_run"], "%Y-%m-%dT%H:%M:%S.%f"
            )
            if next_run > current_time:
                continue  # Skip job as expected next_run hasn't yet passed
        if job.run(cfg):
            # Persist last_run and next_run UTC-based times on job success.
            jobs_status[job.name] = {
                "last_run": current_time,
                "next_run": current_time
                + timedelta(seconds=job.run_interval_seconds(cfg)),
            }
    cfg.write_cache(key="jobs-status", content=jobs_status)


if __name__ == "__main__":
    cfg = UAConfig()
    current_time = datetime.utcnow()
    setup_logging(logging.INFO, logging.DEBUG)
    run_jobs(cfg=cfg, current_time=current_time)
