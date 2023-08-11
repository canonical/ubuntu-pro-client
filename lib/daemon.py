import logging
import os
import sys

from systemd.daemon import notify  # type: ignore

from ubuntupro import defaults, http
from ubuntupro.config import UAConfig
from ubuntupro.daemon import (
    poll_for_pro_license,
    retry_auto_attach,
    setup_logging,
)

LOG = logging.getLogger("ubuntupro.lib.daemon")


def main() -> int:
    setup_logging(
        logging.INFO,
        logging.DEBUG,
        defaults.CONFIG_DEFAULTS["daemon_log_file"],
        logger=LOG,
    )
    cfg = UAConfig()
    setup_logging(
        logging.INFO, logging.DEBUG, log_file=cfg.daemon_log_file, logger=LOG
    )
    # used with loggers in ubuntupro.daemon
    daemon_logger = logging.getLogger("ubuntupro.daemon")
    setup_logging(
        logging.INFO,
        logging.DEBUG,
        log_file=cfg.daemon_log_file,
        logger=daemon_logger,
    )
    # The ua-daemon logger should log everything to its file
    # Make sure the ua-daemon logger does not generate double logging
    # by propagating to the root logger
    LOG.propagate = False
    daemon_logger.propagate = False
    # The root logger should only log errors to the daemon log file
    setup_logging(
        logging.CRITICAL,
        logging.ERROR,
        cfg.daemon_log_file,
    )
    http.configure_web_proxy(cfg.http_proxy, cfg.https_proxy)

    LOG.debug("daemon starting")

    notify("READY=1")

    is_correct_cloud = any(
        os.path.exists("/run/cloud-init/cloud-id-{}".format(cloud))
        for cloud in ("gce", "azure")
    )
    if is_correct_cloud and not os.path.exists(
        retry_auto_attach.FLAG_FILE_PATH
    ):
        LOG.info("mode: poll for pro license")
        poll_for_pro_license.poll_for_pro_license(cfg)

    # not using elif because `poll_for_pro_license` may create the flag file

    if os.path.exists(retry_auto_attach.FLAG_FILE_PATH):
        LOG.info("mode: retry auto attach")
        retry_auto_attach.retry_auto_attach(cfg)

    LOG.debug("daemon ending")
    return 0


if __name__ == "__main__":
    sys.exit(main())
