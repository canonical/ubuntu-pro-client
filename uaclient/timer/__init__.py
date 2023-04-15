import logging
from subprocess import TimeoutExpired

from uaclient import exceptions, system

LOG = logging.getLogger("uaclient.timer")


def start():
    try:
        system.subp(["systemctl", "start", "ua-timer.timer"], timeout=2.0)
    except (exceptions.ProcessExecutionError, TimeoutExpired) as e:
        LOG.warning(e)


def stop():
    try:
        system.subp(["systemctl", "stop", "ua-timer.timer"], timeout=2.0)
    except (exceptions.ProcessExecutionError, TimeoutExpired) as e:
        LOG.warning(e)
