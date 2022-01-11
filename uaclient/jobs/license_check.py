"""
Try to auto-attach in a GCP instance. This should only work
if the instance has a new UA license attached to it
"""
import logging

from uaclient import config, exceptions, jobs
from uaclient.cli import action_auto_attach
from uaclient.clouds.gcp import GCP_LICENSES, UAAutoAttachGCPInstance
from uaclient.clouds.identity import get_cloud_type
from uaclient.util import get_platform_info

LOG = logging.getLogger("ua_lib.license_check.jobs.license_check")


def gcp_auto_attach(cfg: config.UAConfig) -> bool:
    # We will not do anything in a non-GCP cloud
    cloud_id, _ = get_cloud_type()
    if not cloud_id or cloud_id != "gce":
        # If we are not running on GCP cloud, we shouldn't run this
        # job anymore
        LOG.info("Disabling gcp_auto_attach job. Not running on GCP instance")
        jobs.disable_license_check_if_applicable(cfg)
        return False

    # If the instance is already attached we will not do anything.
    # This implies that the user may have a new license attached to the
    # instance, but we will not perfom the change through this job.
    if cfg.is_attached:
        LOG.info("Disabling gcp_auto_attach job. Already attached")
        jobs.disable_license_check_if_applicable(cfg)
        return False

    series = get_platform_info()["series"]
    if series not in GCP_LICENSES:
        LOG.info("Disabling gcp_auto_attach job. Not on LTS")
        jobs.disable_license_check_if_applicable(cfg)
        return False

    # Only try to auto_attach if the license is found in the metadata.
    # If there is a problem finding the metadata, do not error out.
    try:
        licenses = UAAutoAttachGCPInstance().get_licenses_from_identity()
    except Exception:
        return False

    if GCP_LICENSES[series] in licenses:
        try:
            # This function already uses the assert lock decorator,
            # which means that we don't need to make create another
            # lock only for the job
            action_auto_attach(args=None, cfg=cfg)
            return True
        except exceptions.NonAutoAttachImageError:
            # If we get a NonAutoAttachImageError we know
            # that the machine is not ready yet to perform an
            # auto-attach operation (i.e. the license may not
            # have been appended yet). If that happens, we will not
            # error out.
            pass

    return False
