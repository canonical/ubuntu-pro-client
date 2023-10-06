#!/usr/bin/env python3

"""
Perform auto-attach operation

On Ubuntu Pro machines, we try to perform an auto-attach operation
on first boot. This happens through a systemd unit that executes
this script on every boot. However, if we detect
that cloud-init has user data related to ua, we don't run
auto-attach here, since cloud-init will drive this operation on
their side.
"""
import logging
import sys

from uaclient import http, log, messages, system
from uaclient.api.exceptions import (
    AlreadyAttachedError,
    AutoAttachDisabledError,
    EntitlementsNotEnabledError,
)
from uaclient.api.u.pro.attach.auto.full_auto_attach.v1 import (
    FullAutoAttachOptions,
    full_auto_attach,
)
from uaclient.config import UAConfig
from uaclient.daemon import AUTO_ATTACH_STATUS_MOTD_FILE, retry_auto_attach
from uaclient.files import state_files

LOG = logging.getLogger("ubuntupro.lib.auto_attach")

# All known cloud-config keys which provide ubuntu pro configuration directives
CLOUD_INIT_UA_KEYS = set(
    ["ubuntu-advantage", "ubuntu_advantage", "ubuntu_pro"]
)

try:
    import cloudinit.stages as ci_stages  # type: ignore
except ImportError:
    pass


def get_cloudinit_init_stage():
    if "cloudinit.stages" in sys.modules:
        return ci_stages.Init()

    return None


def check_cloudinit_userdata_for_ua_info():
    init = get_cloudinit_init_stage()

    # if init is None, this means we were not able to import the cloud-init
    # module.
    if init is None:
        return False

    if init.cfg and CLOUD_INIT_UA_KEYS.intersection(init.cfg):
        return True

    return False


def main(cfg: UAConfig):
    if check_cloudinit_userdata_for_ua_info():
        LOG.info("cloud-init userdata has ubuntu-advantage key.")
        LOG.info(
            "Skipping auto-attach and deferring to cloud-init "
            "to setup and configure auto-attach"
        )
        return

    system.write_file(
        AUTO_ATTACH_STATUS_MOTD_FILE, messages.AUTO_ATTACH_RUNNING
    )
    try:
        full_auto_attach(FullAutoAttachOptions())
    except AlreadyAttachedError as e:
        LOG.info(e.msg)
    except AutoAttachDisabledError:
        LOG.debug("Skipping auto-attach. Config disable_auto_attach is set.")
    except EntitlementsNotEnabledError as e:
        LOG.warning(e.msg)
    except Exception as e:
        LOG.error(e)
        system.ensure_file_absent(AUTO_ATTACH_STATUS_MOTD_FILE)
        LOG.info("creating flag file to trigger retries")
        system.create_file(retry_auto_attach.FLAG_FILE_PATH)
        failure_reason = (
            retry_auto_attach.full_auto_attach_exception_to_failure_reason(e)
        )
        state_files.retry_auto_attach_state_file.write(
            state_files.RetryAutoAttachState(
                interval_index=0, failure_reason=failure_reason
            )
        )
        return 1

    system.ensure_file_absent(AUTO_ATTACH_STATUS_MOTD_FILE)
    return 0


if __name__ == "__main__":
    log.setup_journald_logging()
    cfg = UAConfig()
    http.configure_web_proxy(cfg.http_proxy, cfg.https_proxy)
    sys.exit(main(cfg))
