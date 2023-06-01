"""
Timer used to run all jobs that need to be frequently run on the system
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from uaclient import defaults
from uaclient.cli import setup_logging
from uaclient.config import UAConfig
from uaclient.exceptions import InvalidFileFormatError
from uaclient.files.state_files import (
    AllTimerJobsState,
    TimerJobState,
    timer_jobs_state_file,
)
from uaclient.timer.metering import metering_enabled_resources
from uaclient.timer.update_contract_info import update_contract_info
from uaclient.timer.update_messaging import update_motd_messages

LOG = logging.getLogger(__name__)
UPDATE_MESSAGING_INTERVAL = 21600  # 6 hours
METERING_INTERVAL = 14400  # 4 hours
UPDATE_CONTRACT_INFO_INTERVAL = 86400  # 24 hours


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
            LOG.debug("Running job: %s", self.name)
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
        run_interval_seconds = super().run_interval_seconds(cfg)

        if run_interval_seconds == 0:
            # If the user has disabled the metering job, we should
            # ignore the activity_ping_interval directive
            return 0

        return max(
            cfg.machine_token_file.activity_ping_interval or 0,
            super().run_interval_seconds(cfg),
        )


metering_job = MeteringTimedJob(metering_enabled_resources, METERING_INTERVAL)
update_message_job = TimedJob(
    "update_messaging",
    update_motd_messages,
    UPDATE_MESSAGING_INTERVAL,
)
update_contract_info_job = TimedJob(
    "update_contract_info",
    update_contract_info,
    UPDATE_CONTRACT_INFO_INTERVAL,
)


def run_job(
    cfg: UAConfig,
    job: TimedJob,
    current_time: datetime,
    job_status: Optional[TimerJobState],
) -> Optional[TimerJobState]:
    if job_status:
        next_run = job_status.next_run
        if next_run and next_run > current_time:
            return job_status
    if job.run(cfg):
        # Persist last_run and next_run UTC-based times on job success.
        last_run = current_time
        next_run = current_time + timedelta(
            seconds=job.run_interval_seconds(cfg)
        )
        job_status = TimerJobState(next_run=next_run, last_run=last_run)

    return job_status


def run_jobs(cfg: UAConfig, current_time: datetime):
    """Run jobs in order when next_run is before current_time.

    Persist jobs-status with calculated next_run values to aid in timer
    state introspection for jobs which have not yet run.
    """
    jobs_status_obj = None
    # If the file format is wrong we remove it, and after the jobs are
    # executed it will be recreated with the proper data.
    try:
        jobs_status_obj = timer_jobs_state_file.read()
    except InvalidFileFormatError:
        try:
            timer_jobs_state_file.delete()
        except (OSError, PermissionError) as exception:
            msg = "Error trying to delete invalid jobs-status.json file: {}"
            msg = msg.format(str(exception))
            LOG.warning(msg)
            return

    if jobs_status_obj is None:
        # We do this for the first run of the timer job, where the file
        # doesn't exist
        jobs_status_obj = AllTimerJobsState(
            metering=None, update_messaging=None, update_contract_info=None
        )

    jobs_status_obj.metering = run_job(
        cfg, metering_job, current_time, jobs_status_obj.metering
    )
    jobs_status_obj.update_messaging = run_job(
        cfg, update_message_job, current_time, jobs_status_obj.update_messaging
    )
    timer_jobs_state_file.write(jobs_status_obj)


if __name__ == "__main__":
    setup_logging(
        logging.CRITICAL,
        logging.DEBUG,
        defaults.CONFIG_DEFAULTS["timer_log_file"],
        logger=LOG,
    )
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
