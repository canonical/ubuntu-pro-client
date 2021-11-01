import logging
import sys

from systemd.daemon import notify  # type: ignore

from uaclient.cli import setup_logging
from uaclient.config import UAConfig

LOG = logging.getLogger("ua_lib.daemon")


def main() -> int:
    cfg = UAConfig()
    setup_logging(
        logging.INFO, logging.DEBUG, log_file=cfg.daemon_log_file, logger=LOG
    )
    # The ua-daemon logger should log everything to its file
    # Make sure the ua-daemon logger does not generate double logging
    # by propagating to the root logger
    LOG.propagate = False
    # The root logger should only log errors to the daemon log file
    setup_logging(
        logging.CRITICAL, logging.ERROR, log_file=cfg.daemon_log_file
    )

    LOG.debug("daemon started")

    notify("READY=1")

    # TODO: actually do something

    return 0


if __name__ == "__main__":
    sys.exit(main())
