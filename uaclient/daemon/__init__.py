import logging
import threading
from typing import List

from uaclient import config

LOG = logging.getLogger("ua.daemon")


def on_start(cfg: config.UAConfig) -> None:
    LOG.debug("daemon.on_start called")


def start_background_threads(cfg: config.UAConfig) -> List[threading.Thread]:
    LOG.debug("daemon.start_background_threads called")
    threads = []  # type: List[threading.Thread]
    return threads


def main_thread(_cfg: config.UAConfig) -> None:
    """
    This function is called after notify("READY=1"). This function should only
    perform tasks that are not important to be finished before systemd
    advertises that the daemon is active and ready.
    """
    LOG.debug("daemon.main_thread called")
