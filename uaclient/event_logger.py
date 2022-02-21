"""
This module is responsible for handling all events
that must be raised to the user somehow. The main idea
behind this module is to centralize all events that happens
during the execution of UA commands and allows us to report
those events in real time or through a machine-readable format.
"""

import enum
import json
import sys
from typing import Dict, List, Optional, Set  # noqa: F401

from uaclient.status import format_machine_readable_output

JSON_SCHEMA_VERSION = "0.1"
_event_logger = None


def get_event_logger():
    global _event_logger

    if _event_logger is None:
        _event_logger = EventLogger()

    return _event_logger


@enum.unique
class EventLoggerMode(enum.Enum):
    """
    Defines event logger supported modes.
    Currently, we only support the cli and machine-readable mode. On cli mode,
    we will print to stdout/stderr any event that we receive. Otherwise, we
    will store those events and parse them for the specified format.
    """

    CLI = object()
    JSON = object()
    YAML = object()


class EventLogger:
    def __init__(self):
        self._error_events = []  # type: List[Dict[str, Optional[str]]]
        self._warning_events = []  # type: List[Dict[str, Optional[str]]]
        self._processed_services = set()  # type: Set[str]
        self._failed_services = set()  # type: Set[str]
        self._needs_reboot = False
        self._command = ""
        self._output_content = {}

        # By default, the event logger will be on CLI mode,
        # printing every event it receives.
        self._event_logger_mode = EventLoggerMode.CLI

    def reset(self):
        """Reset the state of the event logger attributes."""
        self._error_events = []
        self._warning_events = []
        self._processed_services = set()
        self._failed_services = set()
        self._needs_reboot = False
        self._command = ""
        self._output_content = {}
        self._event_logger_mode = EventLoggerMode.CLI

    def set_event_mode(self, event_mode: EventLoggerMode):
        """Set the event logger mode.

        We currently support the CLI, JSON and YAML modes.
        """
        self._event_logger_mode = event_mode

    def set_command(self, command: str):
        """Set the event logger command.

        The command will tell the process_events method which output method
        to use.
        """
        self._command = command

    def set_output_content(self, output_content: Dict):
        """Set the event logger output content.

        The command will tell the process_events method which content
        to use.
        """
        self._output_content = output_content

    def info(self, info_msg: str, file_type=None, end: Optional[str] = None):
        """
        Print the info message if the event logger is on CLI mode.
        """
        if not file_type:
            file_type = sys.stdout

        if self._event_logger_mode == EventLoggerMode.CLI:
            print(info_msg, file=file_type, end=end)

    def _record_dict_event(
        self,
        msg: str,
        service: Optional[str],
        event_dict: List[Dict[str, Optional[str]]],
        code: Optional[str] = None,
        event_type: Optional[str] = None,
    ):
        if event_type is None:
            event_type = "service" if service else "system"

        event_dict.append(
            {
                "type": event_type,
                "service": service,
                "message": msg,
                "message_code": code,
            }
        )

    def error(
        self,
        error_msg: str,
        error_code: Optional[str] = None,
        service: Optional[str] = None,
        error_type: Optional[str] = None,
    ):
        """
        Store an error in the event logger.

        However, the error will only be stored if the event logger
        is not on CLI mode.
        """
        if self._event_logger_mode != EventLoggerMode.CLI:
            self._record_dict_event(
                msg=error_msg,
                service=service,
                event_dict=self._error_events,
                code=error_code,
                event_type=error_type,
            )

    def warning(self, warning_msg: str, service: Optional[str] = None):
        """
        Store a warning in the event logger.

        However, the warning will only be stored if the event logger
        is not on CLI mode.
        """
        if self._event_logger_mode != EventLoggerMode.CLI:
            self._record_dict_event(
                msg=warning_msg,
                service=service,
                event_dict=self._warning_events,
            )

    def service_processed(self, service: str):
        self._processed_services.add(service)

    def services_failed(self, services: List[str]):
        self._failed_services.update(services)

    def service_failed(self, service: str):
        self._failed_services.add(service)

    def needs_reboot(self, reboot_required: bool):
        self._needs_reboot = reboot_required

    def _generate_failed_services(self):
        services_with_error = {
            error["service"]
            for error in self._error_events
            if error["service"]
        }
        return list(set.union(self._failed_services, services_with_error))

    def _process_events_services(self):
        response = {
            "_schema_version": JSON_SCHEMA_VERSION,
            "result": "success" if not self._error_events else "failure",
            "processed_services": sorted(self._processed_services),
            "failed_services": sorted(self._generate_failed_services()),
            "errors": self._error_events,
            "warnings": self._warning_events,
            "needs_reboot": self._needs_reboot,
        }

        print(json.dumps(response, sort_keys=True))

    def _process_events_status(self):
        output = format_machine_readable_output(self._output_content)
        output["result"] = "success" if not self._error_events else "failure"
        output["errors"] = self._error_events
        output["warnings"] = self._warning_events

        if self._event_logger_mode == EventLoggerMode.JSON:
            from uaclient.util import DatetimeAwareJSONEncoder

            print(
                json.dumps(
                    output, cls=DatetimeAwareJSONEncoder, sort_keys=True
                )
            )
        elif self._event_logger_mode == EventLoggerMode.YAML:
            import yaml

            print(yaml.dump(output, default_flow_style=False))

    def process_events(self) -> None:
        """
        Creates a json response based on all of the
        events stored in the event logger.

        The json response will only be created if the event logger
        is not on CLI mode.
        """
        if self._event_logger_mode != EventLoggerMode.CLI:
            if self._command == "status":
                self._process_events_status()
            else:
                self._process_events_services()
