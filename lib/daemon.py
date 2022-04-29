import logging
import sys

from systemd.daemon import notify  # type: ignore

from uaclient import daemon
from uaclient.config import UAConfig
from uaclient.defaults import DEFAULT_LOG_FORMAT

LOG = logging.getLogger("ua")


def setup_logging(console_level, log_level, log_file, logger):
    logger.setLevel(log_level)

    logger.handlers = []

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    console_handler.setLevel(console_level)
    console_handler.set_name("ua-console")
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
    file_handler.set_name("ua-file")
    logger.addHandler(file_handler)


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
