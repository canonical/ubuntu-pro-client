#!/usr/bin/env python

"""
This module is responsible for handling all events
that must be raised to the user somehow. The main idea
behind this module is to centralize all events that happens
during the execution of UA commands and allows us to report
those events in real time or through a machine-readable format.
"""

import enum
import io
import sys
from functools import wraps


@enum.unique
class EventLoggerMode(enum.Enum):
    """
    Defines event logger supported modes.
    Currently, we only support the cli and machine-readable
    mode. On cli mode, we will print to stdout/stderr any
    event that we receive. On machine-readable mode, we will
    store those events and parse them for an specified
    format.
    """

    CLI_MODE = object()
    MACHINE_READABLE_MODE = object()


class StringEvent(io.StringIO):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stdout = sys.stdout

    def write(self, message: str):
        if message.strip():
            sys.stdout = self._stdout
            report_info_event(message)
            sys.stdout = self


class CaptureInfoEvents(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._string_object = StringEvent()
        return self

    def __exit__(self, *args):
        sys.stdout = self._stdout


def capture_info_events(f):
    @wraps(f)
    def new_f(*args, **kwargs):
        with CaptureInfoEvents():
            return f(*args, **kwargs)

    return new_f


# By default, the event logger will be on CLI mode,
# printing every event it receives.
_event_logger_mode = EventLoggerMode.CLI_MODE


def report_info_event(info_msg: str):
    if _event_logger_mode == EventLoggerMode.CLI_MODE:
        print(info_msg)
