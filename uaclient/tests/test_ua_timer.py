import datetime
import logging

import mock
import pytest

from lib.timer import TimedJob, run_jobs


class TestTimedJob:
    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    def test_run_job_returns_true_on_successful_job_run(
        self, FakeConfig, caplog_text
    ):
        """Return True on successful job run."""
        config = FakeConfig()

        def success_job(cfg):
            assert cfg == config

        job = TimedJob("day_job", success_job, 14400)
        assert True is job.run(config)
        assert "Running job: day_job" in caplog_text()

    @pytest.mark.parametrize("caplog_text", [logging.WARNING], indirect=True)
    def test_run_job_returns_false_on_failed_job(
        self, FakeConfig, caplog_text
    ):
        """Return False on failed job run and warns in log."""
        cfg = FakeConfig()

        def failed_job(cfg):
            raise Exception("Something broke")

        job = TimedJob("day_job", failed_job, 14400)
        assert False is job.run(cfg)
        assert "Error executing job day_job: Something broke" in caplog_text()

    @pytest.mark.parametrize("is_cfg_set", (False, True))
    def test_get_default_run_interval(self, is_cfg_set, FakeConfig):
        """Use the default run interval when config is absent or invalid."""
        cfg = FakeConfig()
        if is_cfg_set:
            setattr(cfg, "day_job_timer", None)
        job = TimedJob("day_job", lambda: None, 14400)

        assert 14400 == job.run_interval_seconds(cfg)

    def test_get_configured_run_interval(self, FakeConfig):
        """Use the configured run interval when not overriden."""
        cfg = FakeConfig()
        setattr(cfg, "day_job_timer", 28800)
        job = TimedJob("day_job", lambda: None, 14400)

        assert 28800 == job.run_interval_seconds(cfg)

    @pytest.mark.parametrize(
        "disabled_by_default,interval_value", ((False, 14400), (True, 0))
    )
    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    def test_does_not_run_if_disabled(
        self, FakeConfig, caplog_text, disabled_by_default, interval_value
    ):
        cfg = FakeConfig()
        if not disabled_by_default:
            setattr(cfg, "day_job_timer", 0)

        m_disabled_job = mock.Mock()
        job = TimedJob("day_job", m_disabled_job, interval_value)
        assert False is job.run(cfg)
        assert 0 == m_disabled_job.call_count


class TestTimer:
    @pytest.mark.parametrize("has_next_run", (False, True))
    def test_run_jobs_persists_job_status_on_successful_run(
        self, has_next_run, FakeConfig
    ):
        """Successful job run results in updated job-status.json."""
        cfg = FakeConfig()
        now = datetime.datetime.utcnow()

        if has_next_run:
            cfg.write_cache(
                "jobs-status",
                {"day_job": {"next_run": now - datetime.timedelta(seconds=1)}},
            )

        next_run = now + datetime.timedelta(seconds=43200)
        jobs_status = {
            "day_job": {
                "last_run": now.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                "next_run": next_run.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            }
        }

        m_job_func = mock.Mock()
        m_jobs = [TimedJob("day_job", m_job_func, 43200)]

        with mock.patch("lib.timer.UACLIENT_JOBS", m_jobs):
            run_jobs(cfg, now)

        assert jobs_status == cfg.read_cache("jobs-status")
        assert [mock.call(cfg=cfg)] == m_job_func.call_args_list

    def test_run_job_ignores_late_next_run(self, FakeConfig):
        """Do not run if next_run points to future time."""
        cfg = FakeConfig()
        now = datetime.datetime.utcnow()

        cfg.write_cache(
            "jobs-status",
            {"day_job": {"next_run": now + datetime.timedelta(seconds=14400)}},
        )

        m_job_func = mock.Mock()
        m_jobs = [TimedJob("day_job", m_job_func, 43200)]

        with mock.patch("lib.timer.UACLIENT_JOBS", m_jobs):
            run_jobs(cfg, now)

        assert "last_run" not in cfg.read_cache("jobs-status")["day_job"]
        assert 0 == m_job_func.call_count
