#!/usr/bin/env python3

"""
Run configuration operations during system boot.

Some uaclient operations cannot be fully completed by running a single
command. For example, when upgrading uaclient from trusty to xenial,
we may have a livepatch change in the contract, allowing livepatch to be
enabled on xenial. However, during the upgrade we cannot install livepatch on
the system because the running kernel version will not be updated until reboot.

UA client touches a flag file
/var/lib/ubuntu-advantage/marker-reboot-cmds-required to indicate this script
should run at next boot to process any pending/unresovled config operations.
"""

import logging
import os
import sys
import time

from uaclient import config, contract, entitlements, status
from uaclient.exceptions import UserFacingError, LockHeldError

from uaclient.util import subp, ProcessExecutionError, UrlError
from uaclient.cli import setup_logging, assert_lock_file

# Retry sleep backoff algorithm if lock is held.
# Lock may be held by auto-attach on systems with ubuntu-advantage-pro.
SLEEP_RETRIES_ON_LOCK_HELD = [1, 1, 5]


def run_command(cmd, cfg):
    try:
        out, _ = subp(cmd.split(), capture=True)
        logging.debug("Successfully executed cmd: {}".format(cmd))
    except ProcessExecutionError as exec_error:
        msg = (
            "Failed running cmd: {}\n"
            "Return code: {}\n"
            "Stderr: {}\n"
            "Stdout: {}".format(
                cmd, exec_error.exit_code, exec_error.stderr, exec_error.stdout
            )
        )

        cfg.delete_cache_key("marker-reboot-cmds")

        logging.warning(msg)
        sys.exit(1)


def fix_pro_pkg_holds(cfg):
    status_cache = cfg.read_cache("status-cache")
    if not status_cache:
        return
    for service in status_cache.get("services", []):
        if service.get("name") == "fips":
            service_status = service.get("status")
            if service_status == "enabled":
                ent_cls = entitlements.ENTITLEMENT_CLASS_BY_NAME[
                    service.get("name")
                ]
                logging.debug(
                    "Attempting to remove Ubuntu Pro FIPS package holds"
                )
                entitlement = ent_cls(cfg)
                try:
                    entitlement.setup_apt_config()  # Removes package holds
                    logging.debug(
                        "Successfully removed Ubuntu Pro FIPS package holds"
                    )
                except Exception as e:
                    logging.exception(e)
                    logging.warning(
                        "Could not remove Ubuntu PRO FIPS package holds"
                    )
                try:
                    entitlement.install_packages(cleanup_on_failure=False)
                except UserFacingError as e:
                    logging.error(e.msg)
                    logging.warning(
                        "Failed to install packages at boot: {}".format(
                            ", ".join(entitlement.packages)
                        )
                    )
                    sys.exit(1)
                cfg.remove_notice("", status.MESSAGE_FIPS_REBOOT_REQUIRED)


def refresh_contract(cfg):
    try:
        contract.request_updated_contract(cfg)
    except UrlError as exc:
        logging.exception(exc)
        logging.warning(status.MESSAGE_REFRESH_CONTRACT_FAILURE)
        sys.exit(1)


def process_remaining_deltas(cfg):
    cmd = "/usr/bin/python3 /usr/lib/ubuntu-advantage/upgrade_lts_contract.py"
    run_command(cmd=cmd, cfg=cfg)
    cfg.remove_notice("", status.MESSAGE_LIVEPATCH_LTS_REBOOT_REQUIRED)


@assert_lock_file("ua-reboot-cmds")
def process_reboot_operations(args, cfg):

    setup_logging(logging.INFO, logging.DEBUG)
    reboot_cmd_marker_file = cfg.data_path("marker-reboot-cmds")

    if not cfg.is_attached:
        logging.debug("Skipping reboot_cmds. Machine is unattached")

        if os.path.exists(reboot_cmd_marker_file):
            cfg.delete_cache_key("marker-reboot-cmds")

        return

    if os.path.exists(reboot_cmd_marker_file):
        logging.debug("Running process contract deltas on reboot ...")

        try:
            fix_pro_pkg_holds(cfg)
            refresh_contract(cfg)
            process_remaining_deltas(cfg)

            cfg.delete_cache_key("marker-reboot-cmds")
            cfg.remove_notice("", status.MESSAGE_REBOOT_SCRIPT_FAILED)
            logging.debug("Successfully ran all commands on reboot.")
        except Exception as e:
            msg = "Failed running commands on reboot."
            msg += str(e)
            logging.error(msg)
            cfg.add_notice("", status.MESSAGE_REBOOT_SCRIPT_FAILED)


def main(cfg):
    """Retry running process_reboot_operations on LockHeldError

    :raises: LockHeldError when lock still held by auto-attach after retries.
             UserFacingError for all other errors
    """
    while True:
        try:
            process_reboot_operations(args=None, cfg=cfg)
            break
        except LockHeldError as e:
            logging.debug(
                "Retrying ua-reboot-cmds {} times on held lock".format(
                    len(SLEEP_RETRIES_ON_LOCK_HELD)
                )
            )
            if SLEEP_RETRIES_ON_LOCK_HELD:
                time.sleep(SLEEP_RETRIES_ON_LOCK_HELD.pop(0))
            else:
                logging.warning("Lock not released. %s", str(e.msg))
                sys.exit(1)


if __name__ == "__main__":
    cfg = config.UAConfig()
    main(cfg=cfg)
