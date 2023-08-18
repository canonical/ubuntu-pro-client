import logging
import os
import sys
from subprocess import TimeoutExpired

from uaclient import exceptions
from uaclient import log as pro_log
from uaclient import system, util
from uaclient.config import UAConfig
from uaclient.defaults import DEFAULT_DATA_DIR
from uaclient.log import JsonArrayFormatter

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))

AUTO_ATTACH_STATUS_MOTD_FILE = os.path.join(
    DEFAULT_DATA_DIR, "messages", "motd-auto-attach-status"
)


def start():
    try:
        system.subp(
            ["systemctl", "start", "ubuntu-advantage.service"], timeout=2.0
        )
    except (exceptions.ProcessExecutionError, TimeoutExpired) as e:
        LOG.warning(e, exc_info=e)


def stop():
    try:
        system.subp(
            ["systemctl", "stop", "ubuntu-advantage.service"], timeout=2.0
        )
    except (exceptions.ProcessExecutionError, TimeoutExpired) as e:
        LOG.warning(e, exc_info=e)


def cleanup(cfg: UAConfig):
    from uaclient.daemon import retry_auto_attach

    retry_auto_attach.cleanup(cfg)


def setup_logging(console_level, log_level, log_file, logger=None):
    if logger is None:
        logger = logging.getLogger("ubuntupro")

    logger.setLevel(log_level)

    logger.handlers = []
    logger.addFilter(pro_log.RedactionFilter())

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    console_handler.setLevel(console_level)
    console_handler.set_name("upro-console")
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(JsonArrayFormatter())
    file_handler.setLevel(log_level)
    file_handler.set_name("upro-file")
    logger.addHandler(file_handler)
