#!/usr/bin/env python3

"""
Run configuration operations during system boot.

Some uaclient operations cannot be fully completed by running a single
command. For example, when upgrading uaclient from trusty to xenial,
we may have a livepatch change in the contract, allowing livepatch to be
enabled on xenial. However, during the upgrade we cannot install livepatch on
the system because the running kernel version will not be updated until reboot.

Pro client touches a flag file
/var/lib/ubuntu-advantage/marker-reboot-cmds-required to indicate this script
should run at next boot to process any pending/unresovled config operations.
"""

import logging
import sys

from uaclient import (
    config,
    contract,
    defaults,
    exceptions,
    lock,
    messages,
    upgrade_lts_contract,
)
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.cli import setup_logging
from uaclient.entitlements.fips import FIPSEntitlement
from uaclient.files import notices, state_files


def fix_pro_pkg_holds(cfg: config.UAConfig):
    status_cache = cfg.read_cache("status-cache")
    if not status_cache:
        return
    for service in status_cache.get("services", []):
        if service.get("name") == "fips":
            if service.get("status") == "enabled":
                # fips was enabled, fix the holds
                break
            else:
                # fips was not enabled, don't do anything
                return

    logging.debug("Attempting to remove Ubuntu Pro FIPS package holds")
    fips = FIPSEntitlement(cfg)
    try:
        fips.setup_apt_config()  # Removes package holds
        logging.debug("Successfully removed Ubuntu Pro FIPS package holds")
    except Exception as e:
        logging.error(e)
        logging.warning("Could not remove Ubuntu Pro FIPS package holds")

    try:
        fips.install_packages(cleanup_on_failure=False)
    except exceptions.UserFacingError:
        logging.warning(
            "Failed to install packages at boot: {}".format(
                ", ".join(fips.packages)
            )
        )
        raise


def refresh_contract(cfg: config.UAConfig):
    try:
        contract.request_updated_contract(cfg)
    except exceptions.UrlError:
        logging.warning(messages.REFRESH_CONTRACT_FAILURE)
        raise


def main(cfg: config.UAConfig) -> int:
    if not state_files.reboot_cmd_marker_file.is_present:
        logging.debug("Skipping reboot_cmds. Marker file not present")
        notices.remove(notices.Notice.REBOOT_SCRIPT_FAILED)
        return 0

    if not _is_attached(cfg).is_attached:
        logging.debug("Skipping reboot_cmds. Machine is unattached")
        state_files.reboot_cmd_marker_file.delete()
        notices.remove(notices.Notice.REBOOT_SCRIPT_FAILED)
        return 0

    logging.debug("Running reboot commands...")
    try:
        with lock.SpinLock(cfg=cfg, lock_holder="pro-reboot-cmds"):
            fix_pro_pkg_holds(cfg)
            refresh_contract(cfg)
            upgrade_lts_contract.process_contract_delta_after_apt_lock(cfg)
            # cleanup state after a succesful run
            state_files.reboot_cmd_marker_file.delete()
            notices.remove(notices.Notice.REBOOT_SCRIPT_FAILED)

    except exceptions.LockHeldError as e:
        logging.warning("Lock not released. %s", str(e.msg))
        notices.add(notices.Notice.REBOOT_SCRIPT_FAILED)
        return 1
    except exceptions.UserFacingError as e:
        logging.error(
            "Error while running commands on reboot: %s, %s", e.msg_code, e.msg
        )
        notices.add(notices.Notice.REBOOT_SCRIPT_FAILED)
        return 1
    except Exception as e:
        logging.error("Failed running commands on reboot. Error: %s", str(e))
        notices.add(notices.Notice.REBOOT_SCRIPT_FAILED)
        return 1

    logging.debug("Successfully ran all commands on reboot.")
    return 0


if __name__ == "__main__":
    setup_logging(
        logging.INFO,
        logging.DEBUG,
        defaults.CONFIG_DEFAULTS["log_file"],
    )
    cfg = config.UAConfig()
    setup_logging(logging.INFO, logging.DEBUG, log_file=cfg.log_file)
    sys.exit(main(cfg=cfg))
