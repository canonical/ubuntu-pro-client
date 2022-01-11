"""
Try to auto-attach in a GCP instance. This should only work
if the instance has a new UA license attached to it
"""
import logging

from uaclient.cli import setup_logging
from uaclient.config import UAConfig
from uaclient.jobs.license_check import gcp_auto_attach

LOG = logging.getLogger("ua_lib.license_check")

if __name__ == "__main__":
    cfg = UAConfig()
    # The ua-license-check logger should log everything to its file
    setup_logging(
        logging.CRITICAL,
        logging.DEBUG,
        log_file=cfg.license_check_log_file,
        logger=LOG,
    )
    # Make sure the ua-license-check logger does not generate double logging
    LOG.propagate = False
    # The root logger should log any error to the timer log file
    setup_logging(
        logging.CRITICAL, logging.ERROR, log_file=cfg.license_check_log_file
    )
    gcp_auto_attach(cfg=cfg)
