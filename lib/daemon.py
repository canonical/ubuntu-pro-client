import logging
import os
import sys

from uaclient import http
from uaclient.config import UAConfig
from uaclient.daemon import poll_for_pro_license, retry_auto_attach
from uaclient.log import setup_journald_logging

LOG = logging.getLogger("ubuntupro.daemon")


def main() -> int:
    setup_journald_logging(logging.DEBUG, LOG)
    # Make sure the ubuntupro.daemon logger does not generate double logging
    LOG.propagate = False
    setup_journald_logging(logging.ERROR, logging.getLogger("ubuntupro"))

    cfg = UAConfig()

    http.configure_web_proxy(cfg.http_proxy, cfg.https_proxy)

    LOG.debug("daemon starting")

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
