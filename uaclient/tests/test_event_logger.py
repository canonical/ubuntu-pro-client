import contextlib
import io
import json

import mock
import pytest
import yaml

from uaclient.event_logger import JSON_SCHEMA_VERSION, EventLoggerMode


class TestEventLogger:
    @pytest.mark.parametrize(
        "event_mode",
        (EventLoggerMode.CLI, EventLoggerMode.JSON, EventLoggerMode.YAML),
    )
    def test_process_events(self, event_mode, event):
        with mock.patch.object(event, "_event_logger_mode", event_mode):
            fake_stdout = io.StringIO()
            with contextlib.redirect_stdout(fake_stdout):
                event.info(info_msg="test")
                event.needs_reboot(reboot_required=True)
                event.service_processed("test")
                event.services_failed(["esm"])
                event.error(error_msg="error1")
                event.error(error_msg="error2", service="esm")
                event.error(error_msg="error3", error_type="exception")
                event.warning(warning_msg="warning1")
                event.warning(warning_msg="warning2", service="esm")
                event.process_events()

            expected_cli_out = "test"
            expected_machine_out = {
                "_schema_version": JSON_SCHEMA_VERSION,
                "result": "failure",
                "errors": [
                    {"message": "error1", "service": None, "type": "system"},
                    {"message": "error2", "service": "esm", "type": "service"},
                    {
                        "message": "error3",
                        "service": None,
                        "type": "exception",
                    },
                ],
                "warnings": [
                    {"message": "warning1", "service": None, "type": "system"},
                    {
                        "message": "warning2",
                        "service": "esm",
                        "type": "service",
                    },
                ],
                "failed_services": ["esm"],
                "needs_reboot": True,
                "processed_services": ["test"],
            }

        if event_mode == EventLoggerMode.CLI:
            assert expected_cli_out == fake_stdout.getvalue().strip()
        elif event_mode == EventLoggerMode.JSON:
            assert expected_machine_out == json.loads(
                fake_stdout.getvalue().strip()
            )
        else:
            assert expected_machine_out == yaml.safe_load(
                fake_stdout.getvalue().strip()
            )

    @pytest.mark.parametrize(
        "event_mode",
        (EventLoggerMode.CLI, EventLoggerMode.JSON, EventLoggerMode.YAML),
    )
    def test_process_events_for_status(self, event_mode, event):
        with mock.patch.object(event, "_event_logger_mode", event_mode):
            fake_stdout = io.StringIO()
            with contextlib.redirect_stdout(fake_stdout):
                event.set_command("status")
                event.set_output_content(
                    {
                        "some_status_key": "some_status_information",
                        "a_list_of_things": ["first", "second", "third"],
                    }
                )
                event.info(info_msg="test")
                event.error(error_msg="error1")
                event.warning(warning_msg="warning1")
                event.process_events()

            expected_machine_out = {
                "some_status_key": "some_status_information",
                "a_list_of_things": ["first", "second", "third"],
                "environment_vars": [],
                "services": [],
                "result": "failure",
                "errors": [
                    {"message": "error1", "service": None, "type": "system"}
                ],
                "warnings": [
                    {"message": "warning1", "service": None, "type": "system"}
                ],
            }

            expected_cli_out = "test"

        if event_mode == EventLoggerMode.CLI:
            assert expected_cli_out == fake_stdout.getvalue().strip()
        elif event_mode == EventLoggerMode.JSON:
            assert expected_machine_out == json.loads(
                fake_stdout.getvalue().strip()
            )
        else:
            assert expected_machine_out == yaml.safe_load(
                fake_stdout.getvalue().strip()
            )
