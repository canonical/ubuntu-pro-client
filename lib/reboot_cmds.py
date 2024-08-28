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
    api,
    config,
    contract,
    exceptions,
    http,
    lock,
    log,
    update_contract_info,
    upgrade_lts_contract,
)
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.entitlements.fips import FIPSEntitlement
from uaclient.files import machine_token, notices, state_files

LOG = logging.getLogger("ubuntupro.lib.reboot_cmds")


def fix_pro_pkg_holds(cfg: config.UAConfig):
    status_cache = state_files.status_cache_file.read()
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

    LOG.info("Attempting to remove Ubuntu Pro FIPS package holds")
    fips = FIPSEntitlement(cfg)

    try:
        fips.setup_apt_config(
            progress=api.ProgressWrapper()
        )  # Removes package holds
        LOG.info("Successfully removed Ubuntu Pro FIPS package holds")
    except Exception as e:
        LOG.error(e)
        LOG.warning("Could not remove Ubuntu Pro FIPS package holds")

    try:
        fips.install_packages(
            progress=api.ProgressWrapper(), cleanup_on_failure=False
        )
    except exceptions.UbuntuProError:
        LOG.warning("Failed to install packages at boot: %r", fips.packages)
        raise


def refresh_contract(cfg: config.UAConfig):
    try:
        contract.refresh(cfg)
    except exceptions.ConnectivityError:
        LOG.warning("Failed to refresh contract")
        raise


def handle_unattached_state(cfg: config.UAConfig):
    if not _is_attached(cfg).is_attached:
        LOG.info("Skipping reboot_cmds. Machine is unattached")
        if state_files.reboot_cmd_marker_file.is_present:
            state_files.reboot_cmd_marker_file.delete()
        notices.remove(notices.Notice.REBOOT_SCRIPT_FAILED)
        return 0
    return None


def run_reboot_commands(cfg: config.UAConfig):
    fix_pro_pkg_holds(cfg)
    refresh_contract(cfg)
    upgrade_lts_contract.process_contract_delta_after_apt_lock(cfg)
    state_files.reboot_cmd_marker_file.delete()
    notices.remove(notices.Notice.REBOOT_SCRIPT_FAILED)


def handle_only_series_marker_file(cfg: config.UAConfig):
    """Handle the only_series marker file.
    Checks if the market file is present,
    validates the release series and
    deletes the marker file if the field is not present.""
    """
    if state_files.only_series_check_marker_file.is_present:
        machine_token_file = machine_token.get_machine_token_file()
        only_series = machine_token_file.only_series
        if only_series:
            update_contract_info.validate_release_series(cfg, only_series)
        else:
            state_files.only_series_check_marker_file.delete()


def main(cfg: config.UAConfig) -> int:
    ret = handle_unattached_state(cfg)
    if ret is not None:
        return ret
    try:
        LOG.info("Running commands on reboot")
        with lock.RetryLock(lock_holder="pro-reboot-cmds"):
            handle_only_series_marker_file(cfg)
            if state_files.reboot_cmd_marker_file.is_present:
                run_reboot_commands(cfg)
            else:
                LOG.info("Skipping reboot_cmds. Marker file not present")
                notices.remove(notices.Notice.REBOOT_SCRIPT_FAILED)
                return 0

    except exceptions.LockHeldError as e:
        LOG.warning("Lock not released. %s", str(e.msg))
        notices.add(notices.Notice.REBOOT_SCRIPT_FAILED)
        return 1
    except exceptions.UbuntuProError as e:
        LOG.error(
            "Error while running commands on reboot: %s, %s", e.msg_code, e.msg
        )
        notices.add(notices.Notice.REBOOT_SCRIPT_FAILED)
        return 1
    except Exception as e:
        LOG.error("Failed running commands on reboot. Error: %s", str(e))
        notices.add(notices.Notice.REBOOT_SCRIPT_FAILED)
        return 1

    LOG.info("Successfully ran all commands on reboot.")
    return 0


if __name__ == "__main__":
    log.setup_journald_logging()
    cfg = config.UAConfig()
    http.configure_web_proxy(cfg.http_proxy, cfg.https_proxy)
    sys.exit(main(cfg=cfg))
