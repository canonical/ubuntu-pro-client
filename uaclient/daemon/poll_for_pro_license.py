import logging
import time

from uaclient import actions, exceptions, lock, system, util
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.clouds import AutoAttachInstance
from uaclient.clouds.azure import AzureAutoAttachInstance
from uaclient.clouds.gcp import GCPAutoAttachInstance
from uaclient.clouds.identity import cloud_instance_factory
from uaclient.clouds.lxd import LXDAutoAttachInstance
from uaclient.config import UAConfig
from uaclient.daemon import retry_auto_attach

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


def attempt_auto_attach(cfg: UAConfig, cloud: AutoAttachInstance):
    try:
        with lock.RetryLock(lock_holder="pro.daemon.attempt_auto_attach"):
            actions.auto_attach(cfg, cloud)
    except Exception as e:
        LOG.error(e)
        lock.clear_lock_file_if_present()
        LOG.info("creating flag file to trigger retries")
        system.create_file(retry_auto_attach.FLAG_FILE_PATH)
        return
    LOG.info("Successful auto attach")


def poll_for_pro_license(cfg: UAConfig):
    if util.is_config_value_true(
        config=cfg.cfg, path_to_value="features.disable_auto_attach"
    ):
        LOG.info("Configured to not auto attach, shutting down")
        return
    if _is_attached(cfg).is_attached:
        LOG.info("Already attached, shutting down")
        return
    if not system.is_current_series_lts():
        LOG.info("Not on LTS, shutting down")
        return

    try:
        cloud = cloud_instance_factory()
    except exceptions.CloudFactoryError:
        LOG.info("Not on cloud, shutting down")
        return

    is_supported_cloud = any(
        isinstance(cloud, cloud_instance)
        for cloud_instance in (
            GCPAutoAttachInstance,
            AzureAutoAttachInstance,
            LXDAutoAttachInstance,
        )
    )
    if not is_supported_cloud:
        LOG.info("Not on supported cloud platform, shutting down")
        return

    if not cloud.should_poll_for_pro_license():
        LOG.info("Not on supported instance, shutting down")
        return

    try:
        pro_license_present = cloud.is_pro_license_present(
            wait_for_change=False
        )
    except exceptions.CancelProLicensePolling:
        LOG.info("Cancelling polling")
        return
    except exceptions.DelayProLicensePolling:
        # Continue to polling loop anyway and handle error there if it occurs
        # again
        pass
    else:
        if pro_license_present:
            attempt_auto_attach(cfg, cloud)
            return

    if not cfg.poll_for_pro_license:
        LOG.info("Configured to not poll for pro license, shutting down")
        return

    while True:
        try:
            start = time.time()
            pro_license_present = cloud.is_pro_license_present(
                wait_for_change=True
            )
            end = time.time()
        except exceptions.CancelProLicensePolling:
            LOG.info("Cancelling polling")
            return
        except exceptions.DelayProLicensePolling:
            time.sleep(cfg.polling_error_retry_delay)
            continue
        else:
            if _is_attached(cfg).is_attached:
                # This could have changed during the long poll or sleep
                LOG.info("Already attached, shutting down")
                return
            if pro_license_present:
                attempt_auto_attach(cfg, cloud)
                return
            if end - start < 10:
                LOG.info(
                    "wait_for_change returned quickly and no pro license"
                    " present. Waiting %d seconds before polling again",
                    cfg.polling_error_retry_delay,
                )
                time.sleep(cfg.polling_error_retry_delay)
                continue
