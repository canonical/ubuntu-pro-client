import logging
from subprocess import TimeoutExpired

from uaclient import exceptions, system


def start():
    try:
        system.subp(
            ["systemctl", "start", "pro-auto-attach-retry.service"],
            timeout=2.0,
        )
    except (exceptions.ProcessExecutionError, TimeoutExpired) as e:
        logging.warning(e)


def stop():
    try:
        system.subp(
            ["systemctl", "stop", "pro-auto-attach-retry.service"], timeout=2.0
        )
    except (exceptions.ProcessExecutionError, TimeoutExpired) as e:
        logging.warning(e)
