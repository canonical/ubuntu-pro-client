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

from uaclient import config

from uaclient.util import subp, ProcessExecutionError, del_file
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

        reboot_cmd_marker_file = cfg.data_path("marker-reboot-cmds")
        del_file(reboot_cmd_marker_file)

        logging.debug(msg)
        sys.exit(1)


def refresh_contract(args, cfg):
    cmd = "ua refresh"
    run_command(cmd=cmd, cfg=cfg)


@assert_lock_file("ua-reboot-process-deltas")
def process_remaining_deltas(args, cfg):
    cmd = "/usr/bin/python3 /usr/lib/ubuntu-advantage/upgrade_lts_contract.py"
    run_command(cmd=cmd, cfg=cfg)


def main(args, cfg):
    setup_logging(logging.INFO, logging.DEBUG)
    reboot_cmd_marker_file = cfg.data_path("marker-reboot-cmds")

    if not cfg.is_attached:
        logging.debug("Skiping reboot_cmds. Machine is unattached")

        if os.path.exists(reboot_cmd_marker_file):
            del_file(reboot_cmd_marker_file)

        return

    if os.path.exists(reboot_cmd_marker_file):
        logging.debug(
            "Running process contract deltas on reboot ...".format(
                reboot_cmd_marker_file
            )
        )

        refresh_contract(args, cfg)
        process_remaining_deltas(args, cfg)

        del_file(reboot_cmd_marker_file)

        logging.debug(
            "Completed running process contract deltas on reboot ..."
        )


if __name__ == "__main__":
    cfg = config.UAConfig()
    main(args=None, cfg=cfg)
