"""
Try to auto-attach in a GCP instance. This should only work
if the instance has a new UA license attached to it
"""
import logging

from uaclient import config, exceptions, jobs, util
from uaclient.cli import action_auto_attach, setup_logging
from uaclient.clouds.identity import get_cloud_type
from uaclient.config import UAConfig


def gcp_auto_attach(cfg: config.UAConfig, logger: logging.Logger) -> None:
    # We will not do anything in a non-GCP cloud
    cloud_id, _ = get_cloud_type()
    if not cloud_id or cloud_id != "gce":
        # If we are not running on GCP cloud, we shouldn't run this
        # job anymore
        logger.info(
            "Disabling gcp_auto_attach job. Not running on GCP instance"
        )
        jobs.disable_license_check_if_applicable(cfg)
        return

    # If the instance is already attached we will not do anything.
    # This implies that the user may have a new license attached to the
    # instance, but we will not perfom the change through this job.
    if cfg.is_attached:
        logger.info("Disabling gcp_auto_attach job. Already attached")
        jobs.disable_license_check_if_applicable(cfg)
        return

    try:
        # This function already uses the assert lock decorator,
        # which means that we don't need to make create another
        # lock only for the job
        action_auto_attach(args=None, cfg=cfg)
    except exceptions.NonAutoAttachImageError:
        # If we get a NonAutoAttachImageError we know
        # that the machine is not ready yet to perform an
        # auto-attach operation (i.e. the license may not
        # have been appended yet). If that happens, we will not
        # error out.
        return
