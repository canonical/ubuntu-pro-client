import datetime
import logging
import mock
import pytest

from uaclient.util import parse_rfc3339_date
from lib.timer import run_job


class TestRunJob:
    @pytest.mark.parametrize(
        "last_run,run_interval_seconds,should_run",
        (
            ("2021-07-29T12:00:00Z", 14400, False),
            ("2021-07-29T11:00:00Z", 14400, True),
            ("2021-07-29T12:00:00Z", 3600, True),
        ),
    )
    def test_run_job(self, last_run, run_interval_seconds, should_run):
        last_run = parse_rfc3339_date(last_run)
        next_run = last_run + datetime.timedelta(seconds=run_interval_seconds)
        jobs_status = {
            "test_job": {"last_run": last_run, "next_run": next_run}
        }

        job_func = mock.Mock()
        current_time = parse_rfc3339_date("2021-07-29T15:02:00Z")
        next_run_updated = current_time + datetime.timedelta(
            seconds=run_interval_seconds
        )

        job_ret = run_job(
            job_name="test_job",
            job_func=job_func,
            current_time=current_time,
            run_interval_seconds=run_interval_seconds,
            jobs_status=jobs_status,
            cfg=mock.ANY,
        )

        if should_run:
            assert job_func.call_count == 1
            assert job_ret == {
                "test_job": {
                    "last_run": current_time,
                    "next_run": next_run_updated,
                }
            }
        else:
            assert job_func.call_count == 0
            assert job_ret == {}

    @pytest.mark.parametrize("caplog_text", [logging.WARNING], indirect=True)
    def test_run_job_when_job_fails_to_execute(self, caplog_text):
        job_func = mock.Mock()
        job_func.side_effect = Exception("error")

        assert (
            run_job(
                job_name="test",
                job_func=job_func,
                current_time=mock.ANY,
                run_interval_seconds=60,
                jobs_status={},
                cfg=mock.ANY,
            )
            == {}
        )

        warn_logs = caplog_text()
        assert "Error executing job: test" in warn_logs
