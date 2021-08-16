import datetime
import logging
import mock
import pytest

from lib.timer import (
    run_job,
    run_jobs,
    UPDATE_MESSAGING_INTERVAL,
    UPDATE_STATUS_INTERVAL,
    GCP_AUTO_ATTACH_INTERVAL,
)
from uaclient.jobs.update_messaging import update_apt_and_motd_messages
from uaclient.jobs.update_state import update_status
from uaclient.jobs.gcp_auto_attach import gcp_auto_attach


class TestRunJob:
    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    def test_run_job_returns_true_on_successful_job_run(
        self, FakeConfig, caplog_text
    ):
        """Return True on successful job run."""
        cfg = FakeConfig

        def success_job(config):
            assert config == cfg

        assert True is run_job(
            job_name="Day Job", job_func=success_job, cfg=cfg
        )
        assert "Running job: Day Job" in caplog_text()

    @pytest.mark.parametrize("caplog_text", [logging.WARNING], indirect=True)
    def test_run_job_returns_false_on_failed_job(
        self, FakeConfig, caplog_text
    ):
        """Return False on failed job run and warns in log."""
        cfg = FakeConfig

        def failed_job(config):
            assert config == cfg
            raise Exception("Something broke")

        assert False is run_job(
            job_name="Day Job", job_func=failed_job, cfg=cfg
        )
        assert "Error executing job Day Job: Something broke" in caplog_text()


class TestRunJobs:
    @pytest.mark.parametrize("next_run,call_count", ((None, 1),))
    @mock.patch("lib.timer.run_job")
    def test_run_jobs_persists_job_status_on_successful_run(
        self, run_job, next_run, call_count, FakeConfig
    ):
        """Successful job run results in updated job-status.json."""
        cfg = FakeConfig()
        now = datetime.datetime.utcnow()
        if next_run:
            cfg.write_cache(
                "jobs-status",
                {
                    "update_messaging": {
                        "next_run": now - datetime.timedelta(seconds=1)
                    },
                    "update_status": {
                        "next_run": now - datetime.timedelta(seconds=1)
                    },
                    "gcp_auto_attach": {
                        "next_run": now - datetime.timedelta(seconds=1)
                    },
                },
            )
        run_jobs(cfg=cfg, current_time=now)
        update_messaging_next_run = now + datetime.timedelta(
            seconds=UPDATE_MESSAGING_INTERVAL
        )
        update_status_next_run = now + datetime.timedelta(
            seconds=UPDATE_STATUS_INTERVAL
        )
        gcp_auto_attach_next_run = now + datetime.timedelta(
            seconds=GCP_AUTO_ATTACH_INTERVAL
        )
        jobs_status = {
            "update_messaging": {
                "last_run": now.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                "next_run": update_messaging_next_run.strftime(
                    "%Y-%m-%dT%H:%M:%S.%f"
                ),
            },
            "update_status": {
                "last_run": now.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                "next_run": update_status_next_run.strftime(
                    "%Y-%m-%dT%H:%M:%S.%f"
                ),
            },
            "gcp_auto_attach": {
                "last_run": now.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                "next_run": gcp_auto_attach_next_run.strftime(
                    "%Y-%m-%dT%H:%M:%S.%f"
                ),
            },
        }
        assert jobs_status == cfg.read_cache("jobs-status")
        assert [
            mock.call(
                job_name="update_messaging",
                job_func=update_apt_and_motd_messages,
                cfg=cfg,
            ),
            mock.call(
                job_name="update_status", job_func=update_status, cfg=cfg
            ),
            mock.call(
                job_name="gcp_auto_attach", job_func=gcp_auto_attach, cfg=cfg
            ),
        ] == run_job.call_args_list
