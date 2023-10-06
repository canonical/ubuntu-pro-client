import logging
import os
from subprocess import TimeoutExpired

from uaclient import exceptions, system, util
from uaclient.config import UAConfig
from uaclient.defaults import DEFAULT_DATA_DIR

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
