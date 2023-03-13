import enum
import json
import logging
import pathlib
import sys
from collections import OrderedDict
from typing import Optional  # noqa
from typing import Any, Dict  # noqa: F401

from uaclient import config, util
from uaclient.defaults import CONFIG_DEFAULTS


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


class LogFile(enum.Enum):
    MAIN = 0
    TIMER = 1
    DAEMON = 2

    def default_file(self) -> str:
        if self == self.MAIN:
            return CONFIG_DEFAULTS["log_file"]
        raise NotImplementedError("Implement me for {}".format(self))

    def extract_log_file(self, ua_cfg: config.UAConfig) -> str:
        if self == self.MAIN:
            return ua_cfg.log_file
        raise NotImplementedError("Implement me for {}".format(self))


def setup_logging(console_level, log_level, log_file=None, logger=None):
    """Setup console logging and debug logging to log_file"""
    if log_file is None:
        cfg = config.UAConfig()
        log_file = cfg.log_file
    console_formatter = util.LogFormatter()
    if logger is None:
        # Then we configure the root logger
        logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.addFilter(RedactionFilter())

    # Clear all handlers, so they are replaced for this logger
    logger.handlers = []

    # Setup console logging
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(console_level)
    console_handler.set_name("ua-console")  # Used to disable console logging
    logger.addHandler(console_handler)

    # Setup file logging
    if util.we_are_currently_root():
        # Setup readable-by-root-only debug file logging if running as root
        log_file_path = pathlib.Path(log_file)

        if not log_file_path.exists():
            log_file_path.touch()
            log_file_path.chmod(0o644)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JsonArrayFormatter())
        file_handler.setLevel(log_level)
        file_handler.set_name("ua-file")
        logger.addHandler(file_handler)


class EarlyLoggingSetup:
    def __init__(
        self, console_level, log_level, log_file: LogFile, logger=None
    ):
        self.console_level = console_level
        self.log_level = log_level
        self.log_file = log_file
        self.logger = logger
        self.ua_cfg = None  # type: Optional[config.UAConfig]

    def __enter__(self):
        log_file = self.log_file.default_file()
        setup_logging(
            self.console_level, self.log_level, log_file, self.logger
        )
        return self

    def __exit__(self, type, _value, _traceback):
        if type is not None:
            # A exception happened during the lifetime of this context manager.
            # We shouldn't try to config the final logger, as the exception
            # could come from UAConfig reading.
            return
        ua_cfg = self.ua_cfg or config.UAConfig()
        log_file = self.log_file.extract_log_file(ua_cfg)
        setup_logging(
            self.console_level, self.log_level, log_file, self.logger
        )
