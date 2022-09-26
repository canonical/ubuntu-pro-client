import logging
import time

from uaclient import actions, exceptions, lock, system, util
from uaclient.clouds import AutoAttachCloudInstance
from uaclient.clouds.gcp import UAAutoAttachGCPInstance
from uaclient.clouds.identity import cloud_instance_factory
from uaclient.config import UAConfig
from uaclient.daemon import retry_auto_attach

LOG = logging.getLogger("pro.daemon.poll_for_pro_license")


def attempt_auto_attach(cfg: UAConfig, cloud: AutoAttachCloudInstance):
    try:
        with lock.SpinLock(
            cfg=cfg, lock_holder="pro.daemon.attempt_auto_attach"
        ):
            actions.auto_attach(cfg, cloud)
    except Exception as e:
        LOG.error(e)
        lock.clear_lock_file_if_present()
        LOG.info("creating flag file to trigger retries")
        system.create_file(retry_auto_attach.FLAG_FILE_PATH)
        return
    LOG.debug("Successful auto attach")


def poll_for_pro_license(cfg: UAConfig):
    if util.is_config_value_true(
        config=cfg.cfg, path_to_value="features.disable_auto_attach"
    ):
        LOG.debug("Configured to not auto attach, shutting down")
        return
    if cfg.is_attached:
        LOG.debug("Already attached, shutting down")
        return
    if not system.is_current_series_lts():
        LOG.debug("Not on LTS, shutting down")
        return

    try:
        cloud = cloud_instance_factory()
    except exceptions.CloudFactoryError:
        LOG.debug("Not on cloud, shutting down")
        return

    if not isinstance(cloud, UAAutoAttachGCPInstance):
        LOG.debug("Not on gcp, shutting down")
        return

    if not cloud.should_poll_for_pro_license():
        LOG.debug("Not on supported instance, shutting down")
        return

    try:
        pro_license_present = cloud.is_pro_license_present(
            wait_for_change=False
        )
    except exceptions.CancelProLicensePolling:
        LOG.debug("Cancelling polling")
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
        LOG.debug("Configured to not poll for pro license, shutting down")
        return

    while True:
        try:
            start = time.time()
            pro_license_present = cloud.is_pro_license_present(
                wait_for_change=True
            )
            end = time.time()
        except exceptions.CancelProLicensePolling:
            LOG.debug("Cancelling polling")
            return
        except exceptions.DelayProLicensePolling:
            time.sleep(cfg.polling_error_retry_delay)
            continue
        else:
            if cfg.is_attached:
                # This could have changed during the long poll or sleep
                LOG.debug("Already attached, shutting down")
                return
            if pro_license_present:
                attempt_auto_attach(cfg, cloud)
                return
            if end - start < 10:
                LOG.debug(
                    "wait_for_change returned quickly and no pro license"
                    " present. Waiting {} seconds before polling again".format(
                        cfg.polling_error_retry_delay
                    )
                )
                time.sleep(cfg.polling_error_retry_delay)
                continue
