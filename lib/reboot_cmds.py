#!/usr/bin/env python3

"""
Some uaclient operations cannot be fully completed by running a single
command. For example, when upgrading uaclient from trusty to xenial,
we may have a livepatch change in the contract, allowing livepatch to be
enabled on xenial. However, during the upgrade we cannot install livepatch on
the system, only after a reboot.

To allow uaclient to postpone commands that need to be executed in a system boot,
we are using this script, which will basically try to reprocess contract deltas
on boot time.
"""
import logging
import os
import sys

from uaclient import config, entitlements, status
from uaclient.exceptions import UserFacingError

from uaclient.util import subp, ProcessExecutionError
from uaclient.cli import setup_logging, assert_lock_file


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


@assert_lock_file("ua-reboot-fix-pro-pkg-holds")
def fix_pro_pkg_holds(args, cfg):
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
                except:
                    logging.warning(
                        "Failed to remove Ubuntu PRO FIPS package holds"
                    )
                try:
                    entitlement.install_packages(cleanup_on_failure=False)
                except UserFacingError as e:
                    logging.warning(
                        "Failed to install packages at boot: {}".format(
                            ", ".join(entitlement.packages)
                        )
                    )
                    sys.exit(1)
                cfg.remove_notice("", status.MESSAGE_FIPS_REBOOT_REQUIRED)


def refresh_contract(args, cfg):
    cmd = "ua refresh"
    run_command(cmd=cmd, cfg=cfg)


@assert_lock_file("ua-reboot-process-deltas")
def process_remaining_deltas(args, cfg):
    cmd = "/usr/bin/python3 /usr/lib/ubuntu-advantage/upgrade_lts_contract.py"
    run_command(cmd=cmd, cfg=cfg)
    cfg.remove_notice("", status.MESSAGE_LIVEPATCH_LTS_REBOOT_REQUIRED)


def main(args, cfg):
    setup_logging(logging.INFO, logging.DEBUG)
    reboot_cmd_marker_file = cfg.data_path("marker-reboot-cmds")

    if not cfg.is_attached:
        logging.debug("Skipping reboot_cmds. Machine is unattached")

        if os.path.exists(reboot_cmd_marker_file):
            cfg.delete_cache_key("marker-reboot-cmds")

        return

    if os.path.exists(reboot_cmd_marker_file):
        logging.debug("Running process contract deltas on reboot ...")

        fix_pro_pkg_holds(args, cfg)
        refresh_contract(args, cfg)
        process_remaining_deltas(args, cfg)

        cfg.delete_cache_key("marker-reboot-cmds")

        logging.debug(
            "Completed running process contract deltas on reboot ..."
        )


if __name__ == "__main__":
    cfg = config.UAConfig()
    main(args=None, cfg=cfg)
