import json
import logging
import os
import pathlib
from collections import OrderedDict
from typing import Any, Dict, List, Union  # noqa: F401

from uaclient import defaults, secret_manager, system, util
from uaclient.config import UAConfig


class RegexRedactionFilter(logging.Filter):
    """A logging filter to redact confidential info"""

    def filter(self, record: logging.LogRecord):
        record.msg = util.redact_sensitive_logs(str(record.msg))
        return True


class KnownSecretRedactionFilter(logging.Filter):
    """A logging filter to redact confidential info"""

    def filter(self, record: logging.LogRecord):
        record.msg = secret_manager.secrets.redact_secrets(str(record.msg))
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


def get_user_or_root_log_file_path() -> str:
    """
    Gets the correct log_file path,
    adjusting for whether the user is root or not.
    """
    if util.we_are_currently_root():
        return UAConfig().log_file
    else:
        return get_user_log_file()


def get_user_log_file() -> str:
    """Gets the correct user log_file storage location"""
    return os.path.join(system.get_user_cache_dir(), "ubuntu-pro.log")


def get_all_user_log_files() -> List[str]:
    """Gets all the log files for the users in the system

    Returns a list of all user log files in their home directories.
    """
    user_directories = os.listdir("/home")
    log_files = []
    for user_directory in user_directories:
        user_path = os.path.join(
            "/home",
            user_directory,
            ".cache",
            defaults.USER_CACHE_SUBDIR,
            "ubuntu-pro.log",
        )
        if os.path.isfile(user_path):
            log_files.append(user_path)
    return log_files


def setup_journald_logging():
    logger = logging.getLogger("ubuntupro")
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JsonArrayFormatter())
    console_handler.setLevel(logging.INFO)
    console_handler.addFilter(RegexRedactionFilter())
    console_handler.addFilter(KnownSecretRedactionFilter())
    logger.addHandler(console_handler)


def setup_cli_logging(log_level: Union[str, int], log_file: str):
    """Setup logging to log_file

    If run as non-root then log_file is replaced with a user-specific log file.
    """
    # support lower-case log_level config value
    if isinstance(log_level, str):
        log_level = log_level.upper()

    # if we are running as non-root, change log file
    if not util.we_are_currently_root():
        log_file = get_user_log_file()

    logger = logging.getLogger("ubuntupro")
    logger.setLevel(log_level)

    # Clear all handlers, so they are replaced for this logger
    logger.handlers = []

    # Setup file logging
    log_file_path = pathlib.Path(log_file)
    if not log_file_path.exists():
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        log_file_path.touch(mode=0o640)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(JsonArrayFormatter())
    file_handler.setLevel(log_level)
    file_handler.addFilter(RegexRedactionFilter())
    file_handler.addFilter(KnownSecretRedactionFilter())

    logger.addHandler(file_handler)
