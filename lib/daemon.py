import logging
import os
import sys

from systemd.daemon import notify  # type: ignore

from uaclient import defaults, http
from systemd import journal  # type: ignore
from uaclient.config import UAConfig
from uaclient.daemon import poll_for_pro_license, retry_auto_attach

LOG = logging.getLogger("ubuntupro.daemon")
root_logger = logging.getLogger("ubuntupro")
LOG.addHandler(journal.JournalHandler(SYSLOG_IDENTIFIER="ubuntu-pro-client"))
root_logger.addHandler(
    journal.JournalHandler(SYSLOG_IDENTIFIER="ubuntu-pro-client")
)


def main() -> int:
    LOG.setLevel(logging.DEBUG)
    cfg = UAConfig()
    LOG.setLevel(logging.DEBUG)
    # The ua-daemon logger should log everything to its file
    # Make sure the ua-daemon logger does not generate double logging
    # by propagating to the root logger
    LOG.propagate = False
    root_logger.setLevel(logging.ERROR)

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
