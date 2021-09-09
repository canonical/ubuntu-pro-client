"""
Try to auto-attach in a GCP instance. This should only work
if the instance has a new UA license attached to it
"""
import logging

from uaclient.cli import setup_logging
from uaclient.config import UAConfig
from uaclient.jobs.license_check import gcp_auto_attach

LOG = logging.getLogger(__name__)

if __name__ == "__main__":
    cfg = UAConfig()
    setup_logging(logging.INFO, logging.DEBUG)
    gcp_auto_attach(cfg=cfg, logger=LOG)
