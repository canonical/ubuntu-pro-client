import logging
import threading
from typing import List

from uaclient import config
from uaclient.daemon import license_check

LOG = logging.getLogger("ua.daemon")


def on_start(cfg: config.UAConfig) -> None:
    LOG.debug("daemon.on_start called")
    license_check.check_license(cfg)


def start_background_threads(cfg: config.UAConfig) -> List[threading.Thread]:
    LOG.debug("daemon.start_background_threads called")
    threads = []  # type: List[threading.Thread]

    if license_check.should_poll(cfg):
        fn = license_check.get_polling_fn(cfg)
        if fn:
            LOG.debug("starting license check polling thread")
            thread = threading.Thread(target=fn)
            thread.start()
            threads.append(thread)

    return threads


def main_thread(_cfg: config.UAConfig) -> None:
    """
    This function is called after notify("READY=1"). This function should only
    perform tasks that are not important to be finished before systemd
    advertises that the daemon is active and ready.
    """
    LOG.debug("daemon.main_thread called")
