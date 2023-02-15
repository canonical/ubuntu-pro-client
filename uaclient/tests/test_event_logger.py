import contextlib
import io
import json

import mock
import pytest

from uaclient import yaml
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
                event.error(error_msg="error1", error_code="error1-code")
                event.error(error_msg="error2", service="esm")
                event.error(error_msg="error3", error_type="exception")
                event.error(error_msg="error4", additional_info={"test": 123})
                event.warning(warning_msg="warning1")
                event.warning(warning_msg="warning2", service="esm")
                event.process_events()

            expected_cli_out = "test"
            expected_machine_out = {
                "_schema_version": JSON_SCHEMA_VERSION,
                "result": "failure",
                "errors": [
                    {
                        "message": "error1",
                        "message_code": "error1-code",
                        "service": None,
                        "type": "system",
                    },
                    {
                        "message": "error2",
                        "message_code": None,
                        "service": "esm",
                        "type": "service",
                    },
                    {
                        "message": "error3",
                        "message_code": None,
                        "service": None,
                        "type": "exception",
                    },
                    {
                        "message": "error4",
                        "message_code": None,
                        "service": None,
                        "type": "system",
                        "additional_info": {"test": 123},
                    },
                ],
                "warnings": [
                    {
                        "message": "warning1",
                        "message_code": None,
                        "service": None,
                        "type": "system",
                    },
                    {
                        "message": "warning2",
                        "message_code": None,
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
        "env_return,env_list",
        (
            ({}, []),
            (
                {"UA_EXAMPLE_KEY1": "value1", "UA_EXAMPLE_KEY2": "value2"},
                [
                    {"name": "UA_EXAMPLE_KEY1", "value": "value1"},
                    {"name": "UA_EXAMPLE_KEY2", "value": "value2"},
                ],
            ),
        ),
    )
    @pytest.mark.parametrize(
        "event_mode",
        (EventLoggerMode.CLI, EventLoggerMode.JSON, EventLoggerMode.YAML),
    )
    @mock.patch("uaclient.util.get_pro_environment")
    def test_process_events_for_status(
        self, m_environment, event_mode, env_return, env_list, event
    ):
        m_environment.return_value = env_return
        with mock.patch.object(event, "_event_logger_mode", event_mode):
            fake_stdout = io.StringIO()
            with contextlib.redirect_stdout(fake_stdout):
                event.set_command("status")
                event.set_output_content(
                    {
                        "some_status_key": "some_status_information",
                        "a_list_of_things": ["first", "second", "third"],
                        "services": [],
                    }
                )
                event.info(info_msg="test")
                event.error(error_msg="error1")
                event.warning(warning_msg="warning1")
                event.process_events()

            expected_machine_out = {
                "some_status_key": "some_status_information",
                "a_list_of_things": ["first", "second", "third"],
                "environment_vars": env_list,
                "services": [],
                "result": "failure",
                "errors": [
                    {
                        "message": "error1",
                        "message_code": None,
                        "service": None,
                        "type": "system",
                    }
                ],
                "warnings": [
                    {
                        "message": "warning1",
                        "message_code": None,
                        "service": None,
                        "type": "system",
                    }
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
