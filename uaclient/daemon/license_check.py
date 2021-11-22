import logging
from typing import Callable, Optional

from uaclient import actions, config, exceptions, lock, util
from uaclient.clouds import AutoAttachCloudInstance
from uaclient.clouds.identity import cloud_instance_factory

LOG = logging.getLogger("ua.daemon.license_check")


def _get_cloud(cfg) -> Optional[AutoAttachCloudInstance]:
    try:
        return cloud_instance_factory(cfg)
    except exceptions.CloudFactoryError:
        return None


def check_license(cfg: config.UAConfig) -> None:
    cloud = _get_cloud(cfg)
    if not cloud:
        return None
    if cloud.is_license_present():
        try:
            with lock.SpinLock(
                cfg=cfg, lock_holder="ua.daemon.license_check.check_license"
            ):
                actions.auto_attach(cfg, cloud)
        except Exception as e:
            # TODO: is there anything else to do here?
            lock.clear_lock_file_if_present()
            LOG.exception(e)


def should_poll(cfg: config.UAConfig) -> bool:
    if any(
        [
            not cfg.should_poll_for_licenses,
            util.is_config_value_true(
                config=cfg.cfg, path_to_value="features.disable_auto_attach"
            ),
            cfg.is_attached,
            not util.is_current_series_lts(),
        ]
    ):
        return False

    cloud = _get_cloud(cfg)
    if not cloud:
        return False

    return cloud.should_poll_for_license()


def get_polling_fn(cfg) -> Optional[Callable]:
    cloud = _get_cloud(cfg)
    if not cloud:
        return None
    return cloud.get_polling_fn()
