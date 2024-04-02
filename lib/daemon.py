import logging
import os
import sys
import time

from uaclient import http, log, system
from uaclient.config import UAConfig
from uaclient.daemon import poll_for_pro_license, retry_auto_attach

LOG = logging.getLogger("ubuntupro.daemon")


# 10 seconds times 120 = 20 minutes
WAIT_FOR_CLOUD_CONFIG_SLEEP_TIME = 10
WAIT_FOR_CLOUD_CONFIG_POLL_TIMES = 120


def _wait_for_cloud_config():
    LOG.debug("waiting for cloud-config.service to finish")
    for i in range(WAIT_FOR_CLOUD_CONFIG_POLL_TIMES + 1):
        state = system.get_systemd_unit_active_state("cloud-config.service")
        ci_state = system.get_systemd_unit_active_state("cloud-init.service")
        LOG.debug("cloud-config.service state: %r", state)
        LOG.debug("cloud-init.service state: %r", ci_state)
        # if cloud-config.service is not yet activating but cloud-init is
        # running, wait for cloud-config to start
        if state == "activating" or (
            state == "inactive"
            and (ci_state == "activating" or ci_state == "active")
        ):
            if i < WAIT_FOR_CLOUD_CONFIG_POLL_TIMES:
                LOG.debug(
                    "cloud-config.service is activating. "
                    "waiting to check again."
                )
                time.sleep(WAIT_FOR_CLOUD_CONFIG_SLEEP_TIME)
            else:
                LOG.warning(
                    "cloud-config.service is still activating after "
                    "20 minutes. continuing anyway"
                )
                return
        else:
            LOG.debug("cloud-config.service is not activating. continuing")
            return


def main() -> int:
    log.setup_journald_logging()

    cfg = UAConfig()

    http.configure_web_proxy(cfg.http_proxy, cfg.https_proxy)

    LOG.info("daemon starting")

    _wait_for_cloud_config()

    LOG.debug("checking for condition files")
    is_correct_cloud = any(
        os.path.exists("/run/cloud-init/cloud-id-{}".format(cloud))
        for cloud in ("gce", "azure")
    )
    if is_correct_cloud and not os.path.exists(
        retry_auto_attach.FLAG_FILE_PATH
    ):
        LOG.info("mode: poll for pro license")
        poll_for_pro_license.poll_for_pro_license(cfg)

    # not using elif because `poll_for_pro_license` may create the flag file

    if os.path.exists(retry_auto_attach.FLAG_FILE_PATH):
        LOG.info("mode: retry auto attach")
        retry_auto_attach.retry_auto_attach(cfg)

    LOG.info("daemon ending")
    return 0


if __name__ == "__main__":
    sys.exit(main())
