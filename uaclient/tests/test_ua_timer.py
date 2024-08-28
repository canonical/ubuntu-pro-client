import datetime
import logging

import mock
import pytest

from lib import timer
from lib.timer import MeteringTimedJob, TimedJob, run_jobs
from uaclient.exceptions import InvalidFileFormatError


class TestTimedJob:
    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @pytest.mark.parametrize("return_value", (True, False))
    def test_run_job_returns_true_on_successful_job_run(
        self, return_value, caplog_text, FakeConfig
    ):
        """Return True on successful job run."""
        config = FakeConfig()

        def success_job(cfg):
            assert cfg == config
            return return_value

        job = TimedJob("day_job", success_job, 14400)
        assert True is job.run(config)

        if return_value:
            # Job executed
            assert "Executed job: day_job" in caplog_text()
        else:
            # Job noops
            assert "Executed job: day_job" not in caplog_text()

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

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @pytest.mark.parametrize("is_cfg_set", (False, True))
    def test_get_default_run_interval(
        self, is_cfg_set, caplog_text, FakeConfig
    ):
        """Use the default run interval when config is absent or invalid."""
        cfg = FakeConfig()
        if is_cfg_set:
            setattr(cfg, "day_job_timer", -3)
        job = TimedJob("day_job", lambda: None, 14400)

        assert 14400 == job.run_interval_seconds(cfg)
        if is_cfg_set:
            assert (
                "Invalid value for day_job interval found in config."
                in caplog_text()
            )

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
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        # we lose microseconds when deserializing
        now = now - datetime.timedelta(microseconds=now.microsecond)
        fake_file = mock.MagicMock()
        m_job_status = mock.MagicMock(next_run=None, last_run=None)

        if has_next_run:
            next_run = now - datetime.timedelta(seconds=1)
            m_job_status.next_run = next_run

        fake_file.read.return_value = mock.MagicMock(
            metering=m_job_status,
            update_messaging=None,
        )
        expected_next_run = now + datetime.timedelta(seconds=43200)

        m_job_func = mock.Mock()
        m_jobs = TimedJob("fake_job", m_job_func, 43200)

        with mock.patch("lib.timer.metering_job", m_jobs):
            with mock.patch.object(timer, "timer_jobs_state_file", fake_file):
                run_jobs(cfg, now)

        actual_job_state = fake_file.read().metering
        assert expected_next_run == actual_job_state.next_run
        assert [mock.call(cfg=cfg)] == m_job_func.call_args_list

    def test_run_job_ignores_late_next_run(self, FakeConfig):
        """Do not run if next_run points to future time."""
        cfg = FakeConfig()
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        # we lose microseconds when deserializing
        now = now - datetime.timedelta(microseconds=now.microsecond)

        fake_file = mock.MagicMock()
        m_job_status = mock.MagicMock(
            next_run=now + datetime.timedelta(seconds=14400), last_run=None
        )
        fake_file.read.return_value = mock.MagicMock(
            metering=m_job_status,
            update_messaging=None,
        )

        m_job_func = mock.Mock()
        m_job = TimedJob("metering", m_job_func, 43200)

        with mock.patch("lib.timer.metering_job", m_job):
            with mock.patch.object(timer, "timer_jobs_state_file", fake_file):
                run_jobs(cfg, now)

        actual_job_state = fake_file.read().metering
        assert actual_job_state.last_run is None
        assert 0 == m_job_func.call_count

    @pytest.mark.parametrize(
        "delete_side_effect", (None, OSError(), PermissionError())
    )
    @pytest.mark.parametrize("caplog_text", [logging.WARNING], indirect=True)
    @mock.patch("lib.timer.AllTimerJobsState")
    @mock.patch("lib.timer.run_job")
    def test_run_jobs_tries_to_create_new_file_when_invalid(
        self,
        m_run_job,
        m_jobs_state,
        delete_side_effect,
        caplog_text,
        FakeConfig,
    ):
        cfg = FakeConfig()
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        # we lose microseconds when deserializing
        now = now - datetime.timedelta(microseconds=now.microsecond)

        fake_file = mock.MagicMock()
        fake_file.read.side_effect = InvalidFileFormatError(
            file_name="file", file_format="json"
        )
        fake_file.delete.side_effect = delete_side_effect

        with mock.patch.object(timer, "timer_jobs_state_file", fake_file):
            run_jobs(cfg, now)

        assert [mock.call()] == fake_file.delete.call_args_list
        if delete_side_effect is None:
            assert [
                mock.call(m_jobs_state())
            ] == fake_file.write.call_args_list
            assert 2 == m_run_job.call_count
        else:
            assert [] == fake_file.write.call_args_list
            assert 0 == m_run_job.call_count
            log = caplog_text()
            assert (
                "Error trying to delete invalid jobs-status.json file" in log
            )


class TestMeteringTimedJob:
    @pytest.mark.parametrize(
        "activity_ping_interval_value,config_value,expected_value",
        ((None, 100, 100), (20, 80, 80), (1000, 80, 1000), (1000, 0, 0)),
    )
    @mock.patch("lib.timer.TimedJob.run_interval_seconds")
    def test_metering_run_interval_seconds(
        self,
        m_run_interval_seconds,
        activity_ping_interval_value,
        config_value,
        expected_value,
        fake_machine_token_file,
    ):
        m_run_interval_seconds.return_value = config_value
        m_cfg = mock.MagicMock()
        fake_machine_token_file.attached = True
        fake_machine_token_file.token = {
            "activityInfo": {
                "activityPingInterval": activity_ping_interval_value
            }
        }

        metering_job = MeteringTimedJob(
            job_func=mock.MagicMock(),
            default_interval_seconds=mock.MagicMock(),
        )
        assert expected_value == metering_job.run_interval_seconds(m_cfg)
