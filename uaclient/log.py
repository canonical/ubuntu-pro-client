import json
import logging
from collections import OrderedDict
from typing import Any, Dict  # noqa: F401

from uaclient import util


class RedactionFilter(logging.Filter):
    """A logging filter to redact confidential info"""

    def filter(self, record: logging.LogRecord):
        record.msg = util.redact_sensitive_logs(str(record.msg))
        return True


class JsonArrayFormatter(logging.Formatter):
    """Json Array Formatter for our logging mechanism
    Custom made for Pro logging needs
    """

    default_time_format = "%Y-%m-%dT%H:%M:%S"
    default_msec_format = "%s.%03d"
    required_fields = (
        "asctime",
        "levelname",
        "name",
        "funcName",
        "lineno",
        "message",
    )

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        record.asctime = self.formatTime(record)

        extra_message_dict = {}  # type: Dict[str, Any]
        if record.exc_info:
            extra_message_dict["exc_info"] = self.formatException(
                record.exc_info
            )
        if not extra_message_dict.get("exc_info") and record.exc_text:
            extra_message_dict["exc_info"] = record.exc_text
        if record.stack_info:
            extra_message_dict["stack_info"] = self.formatStack(
                record.stack_info
            )
        extra = record.__dict__.get("extra")
        if extra and isinstance(extra, dict):
            extra_message_dict.update(extra)

        # is ordered to maintain order of fields in log output
        local_log_record = OrderedDict()  # type: Dict[str, Any]
        # update the required fields in the order stated
        for field in self.required_fields:
            value = record.__dict__.get(field)
            local_log_record[field] = value

        local_log_record["extra"] = extra_message_dict
        return json.dumps(list(local_log_record.values()))
