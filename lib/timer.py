"""
Timer used to run all jobs that need to be frequently run on the system
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Callable

from uaclient.cli import setup_logging
from uaclient.config import UAConfig
from uaclient.jobs.metering import metering_enabled_resources
from uaclient.jobs.update_messaging import update_apt_and_motd_messages
from uaclient.jobs.update_state import update_status

LOG = logging.getLogger(__name__)
UPDATE_MESSAGING_INTERVAL = 21600  # 6 hours
UPDATE_STATUS_INTERVAL = 43200  # 12 hours
METERING_INTERVAL = 14400  # 4 hours


class TimedJob:
    def __init__(
        self,
        name: str,
        job_func: Callable[..., bool],
        default_interval_seconds: int,
    ):
        self.name = name
        self._job_func = job_func
        self._default_interval_seconds = default_interval_seconds

    def run(self, cfg: UAConfig) -> bool:
        """Run a job in a failsafe manner, returning True on success.
        Checks if the job is not disabled before running it.

        :param cfg: UAConfig instance

        :return: A bool True when successfully run. False if ignored
            or in error.
        """
        if not self._should_run(cfg):
            return False

        try:
            if self._job_func(cfg=cfg):
                LOG.debug("Executed job: %s", self.name)
        except Exception as e:
            LOG.error("Error executing job %s: %s", self.name, str(e))
            return False

        return True

    def run_interval_seconds(self, cfg: UAConfig) -> int:
        """Return the run_interval for the job based on config or defaults."""
        configured_interval = getattr(cfg, "{}_timer".format(self.name), None)
        if configured_interval is None:
            return self._default_interval_seconds
        if not isinstance(configured_interval, int) or configured_interval < 0:
            warning_msg = (
                "Invalid value for {} interval found in config. "
                "Default value will be used."
            ).format(self.name)
            LOG.warning(warning_msg)
            return self._default_interval_seconds
        return configured_interval

    def _should_run(self, cfg) -> bool:
        """Verify if the job has a valid (non-zero) interval."""
        return self.run_interval_seconds(cfg) != 0


class MeteringTimedJob(TimedJob):
    def __init__(
        self, job_func: Callable[..., bool], default_interval_seconds: int
    ):
        super().__init__(
            name="metering",
            job_func=job_func,
            default_interval_seconds=default_interval_seconds,
        )

    def run_interval_seconds(self, cfg: UAConfig) -> int:
        """
        Define the run interval for the metering job.

        The contract server can control the time we should make the request
        again. Since the user can also configure the timer interval for this
        job, we will select the greater value between those two choices.
        """
        return max(
            cfg.activity_ping_interval or 0, super().run_interval_seconds(cfg)
        )


UACLIENT_JOBS = [
    TimedJob(
        "update_messaging",
        update_apt_and_motd_messages,
        UPDATE_MESSAGING_INTERVAL,
    ),
    TimedJob("update_status", update_status, UPDATE_STATUS_INTERVAL),
    MeteringTimedJob(metering_enabled_resources, METERING_INTERVAL),
]


def run_jobs(cfg: UAConfig, current_time: datetime):
    """Run jobs in order when next_run is before current_time.

    Persist jobs-status with calculated next_run values to aid in timer
    state introspection for jobs which have not yet run.
    """
    jobs_status = cfg.read_cache("jobs-status") or {}
    for job in UACLIENT_JOBS:
        if job.name in jobs_status:
            next_run = jobs_status[job.name]["next_run"]
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
    current_time = datetime.now(timezone.utc)

    # The ua-timer logger should log everything to its file
    setup_logging(
        logging.CRITICAL,
        logging.DEBUG,
        log_file=cfg.timer_log_file,
        logger=LOG,
    )
    # Make sure the ua-timer logger does not generate double logging
    LOG.propagate = False
    # The root logger should log any error to the timer log file
    setup_logging(logging.CRITICAL, logging.ERROR, log_file=cfg.timer_log_file)

    run_jobs(cfg=cfg, current_time=current_time)
