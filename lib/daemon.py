import logging
import os
import sys

from systemd.daemon import notify  # type: ignore

from uaclient import defaults
from uaclient.config import UAConfig
from uaclient.daemon import (
    poll_for_pro_license,
    retry_auto_attach,
    setup_logging,
)

LOG = logging.getLogger("uaclient.lib.daemon")
uaclient_logger = logging.getLogger("uaclient")


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
    # The ua-daemon logger should log everything to its file
    # Make sure the ua-daemon logger does not generate double logging
    # by propagating to the root logger
    # The root logger should only log errors to the daemon log file
    # TODO: is this okay? root_logger("uaclient")
    setup_logging(
        logging.CRITICAL,
        logging.ERROR,
        log_file=cfg.daemon_log_file,
        logger=uaclient_logger,
    )

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
