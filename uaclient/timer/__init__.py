import logging
from subprocess import TimeoutExpired

from uaclient import exceptions, system, util

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


def start():
    try:
        system.subp(["systemctl", "start", "ua-timer.timer"], timeout=2.0)
    except (exceptions.ProcessExecutionError, TimeoutExpired) as e:
        LOG.warning(e, exc_info=e)


def stop():
    try:
        system.subp(["systemctl", "stop", "ua-timer.timer"], timeout=2.0)
    except (exceptions.ProcessExecutionError, TimeoutExpired) as e:
        LOG.warning(e, exc_info=e)
