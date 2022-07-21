#!/usr/bin/env python3

"""
Perform auto-attach operation

On Ubuntu Pro machines, we try to perform an auto-attach operation
on first boot. This happens through a systemd unit that triggers
that executes this script on every boot. However, if we detect
that cloud-init has user data related to ua, we cannot run
auto-attach here, since cloud-init will drive this operation on
their side.
"""
import logging

import yaml

from uaclient.cli import action_auto_attach, setup_logging
from uaclient.config import UAConfig
from uaclient.exceptions import (
    AlreadyAttachedOnPROError,
    ProcessExecutionError,
)
from uaclient.util import subp, which


def check_cloudinit_userdata_for_ua_info():
    if not which("cloud-init"):
        return False

    try:
        userdata, _ = subp(["cloud-init", "query", "userdata"])
    except ProcessExecutionError:
        # if we cannot query the userdata, we should not block auto-attach
        return False

    try:
        userdata_dict = yaml.safe_load(userdata)
    except Exception:
        # if there is any error parsing the userdata, we should not block
        # auto-attach
        return False

    if userdata_dict and "ubuntu_advantage" in userdata_dict.keys():
        return True

    return False


def main(cfg: UAConfig):
    if not check_cloudinit_userdata_for_ua_info():
        # Once we have the api functions ready, we should
        # update this part of the code to not call the cli
        # function directly
        try:
            action_auto_attach(args=None, cfg=cfg)
        except AlreadyAttachedOnPROError as e:
            logging.info(e.msg)
    else:
        auto_attach_msg = (
            "Skipping auto-attach and deferring to cloud-init "
            "to setup and configure auto-attach"
        )

        logging.info("cloud-init userdata has ubuntu-advantage key.")
        logging.info(auto_attach_msg)


if __name__ == "__main__":
    cfg = UAConfig(root_mode=True)
    setup_logging(logging.INFO, logging.DEBUG, log_file=cfg.log_file)
    main(cfg=cfg)
