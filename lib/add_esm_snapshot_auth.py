import logging

from uaclient import config, defaults, log
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.entitlements.entitlement_status import ApplicationStatus
from uaclient.entitlements.esm import ESMAppsEntitlement, ESMInfraEntitlement

LOG = logging.getLogger("ubuntupro.lib.add_esm_snapshot_auth")

ESM_APPS_SNAPSHOT_URLS = [
    "snapshot.apps-security.esm.ubuntu.com/apps/ubuntu/",
    "snapshot.apps-updates.esm.ubuntu.com/apps/ubuntu/",
]
ESM_INFRA_SNAPSHOT_URLS = [
    "snapshot.infra-security.esm.ubuntu.com/infra/ubuntu/",
    "snapshot.infra-updates.esm.ubuntu.com/infra/ubuntu/",
]


def add_esm_snapshot_auth(cfg):
    if not _is_attached(cfg).is_attached:
        LOG.info("Not attached. Not adding ESM snapshot URLs to APT auth.")
        return
    for esm, urls in [
        (ESMAppsEntitlement(cfg), ESM_APPS_SNAPSHOT_URLS),
        (ESMInfraEntitlement(cfg), ESM_INFRA_SNAPSHOT_URLS),
    ]:
        if (
            esm.application_status()[0] != ApplicationStatus.DISABLED
            and esm.apt_url is not None
            and "https://esm.ubuntu.com/" in esm.apt_url
        ):
            LOG.info(
                (
                    "%s is enabled and using default apt url,"
                    " adding snapshot auth"
                ),
                esm.name,
            )
            esm.update_apt_auth(override_snapshot_urls=urls)
        else:
            LOG.info(
                "%s is disabled or not using default apt url, skipping",
                esm.name,
                extra=log.extra(apt_url=esm.apt_url),
            )


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
