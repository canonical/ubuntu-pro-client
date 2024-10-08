import logging

from uaclient import config, defaults, log
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.entitlements.entitlement_status import ApplicationStatus
from uaclient.entitlements.esm import ESMAppsEntitlement, ESMInfraEntitlement

LOG = logging.getLogger("ubuntupro.lib.add_esm_snapshot_auth")


def add_esm_snapshot_auth(cfg):
    if not _is_attached(cfg).is_attached:
        LOG.info("Not attached. Ending.")
        return
    for esm in [ESMAppsEntitlement(cfg), ESMInfraEntitlement(cfg)]:
        if esm.application_status()[0] != ApplicationStatus.DISABLED:
            LOG.info("%s is enabled, adding snapshot auth", esm.name)
            esm.update_apt_auth()
        else:
            LOG.info("%s is disabled, skipping", esm.name)


if __name__ == "__main__":
    try:
        log.setup_cli_logging(
            logging.DEBUG, defaults.CONFIG_DEFAULTS["log_level"]
        )
        cfg = config.UAConfig()
        log.setup_cli_logging(cfg.log_level, cfg.log_file)
        add_esm_snapshot_auth(cfg)
    except Exception as e:
        print(e)
