import logging
import sys

from systemd.daemon import notify  # type: ignore

from uaclient.config import UAConfig
from uaclient.services import daemon, setup_logging

LOG = logging.getLogger("pro")


def main() -> int:

    cfg = UAConfig(root_mode=True)
    setup_logging(
        logging.INFO, logging.DEBUG, log_file=cfg.daemon_log_file, logger=LOG
    )
    # The ua-daemon logger should log everything to its file
    # Make sure the ua-daemon logger does not generate double logging
    # by propagating to the root logger
    LOG.propagate = False
    # The root logger should only log errors to the daemon log file
    setup_logging(
        logging.CRITICAL,
        logging.ERROR,
        log_file=cfg.daemon_log_file,
        logger=logging.getLogger(),
    )

    LOG.debug("daemon starting")

    notify("READY=1")

    daemon.poll_for_pro_license(cfg)

    LOG.debug("daemon ending")
    return 0


if __name__ == "__main__":
    sys.exit(main())
