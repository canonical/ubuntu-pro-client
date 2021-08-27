"""
Try to auto-attach in a GCP instance. This should only work
if the instance has a new UA license attached to it
"""

from uaclient import config, exceptions
from uaclient.cli import action_auto_attach
from uaclient.clouds.identity import get_cloud_type


def gcp_auto_attach(cfg: config.UAConfig) -> None:
    # If the instance is already attached we will not do anything.
    # This implies that the user may have a new license attached to the
    # instance, but we will not perfom the change through this job.
    if cfg.is_attached:
        return

    # We will not do anything in a non-GCP cloud
    cloud_id, _ = get_cloud_type()
    if not cloud_id or cloud_id != "gce":
        return

    try:
        # This function already uses the assert lock decorator,
        # which means that we don't need to make create another
        # lock only for the job
        action_auto_attach(args=None, cfg=cfg)
    except exceptions.NonAutoAttachImageError:
        # If we get a NonAutoAttachImageError we now
        # that the machine is not ready yet to perform an
        # auto-attach operation (i.e. the license may not
        # have been appended yet). If that happens, we will not
        # error out.
        return
