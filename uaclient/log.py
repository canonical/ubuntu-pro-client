import json
import logging
import os
from collections import OrderedDict
from typing import Any, Dict, List  # noqa: F401

from uaclient import defaults, system, util


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


def get_user_log_file() -> str:
    """Gets the correct user log_file storage location"""
    return system.get_user_cache_dir() + "/ubuntu-pro.log"


def get_all_user_log_files() -> List[str]:
    """Gets all the log files for the users in the system

    Returns a list of all user log files in their home directories.
    """
    user_directories = os.listdir("/home")
    log_files = []
    for user_directory in user_directories:
        user_path = (
            "/home/"
            + user_directory
            + "/.cache/"
            + defaults.USER_CACHE_SUBDIR
            + "/ubuntu-pro.log"
        )
        if os.path.isfile(user_path):
            log_files.append(user_path)
    return log_files


def setup_journald_logging(log_level, logger):
    logger.setLevel(log_level)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JsonArrayFormatter())
    console_handler.setLevel(log_level)
    console_handler.addFilter(RedactionFilter())
    logger.addHandler(console_handler)
