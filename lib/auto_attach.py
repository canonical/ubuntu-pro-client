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

from uaclient import actions
from uaclient.api.exceptions import AlreadyAttachedError
from uaclient.api.u.pro.attach.auto.full_auto_attach.v1 import (
    FullAutoAttachOptions,
    full_auto_attach,
)
from uaclient.config import UAConfig
from uaclient.services import setup_logging

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

    if init.cfg and "ubuntu_advantage" in init.cfg.keys():
        return True

    return False


def main(cfg: UAConfig):
    if not check_cloudinit_userdata_for_ua_info():
        if actions.should_disable_auto_attach(cfg):
            return
        try:
            full_auto_attach(FullAutoAttachOptions())
        except AlreadyAttachedError as e:
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
    setup_logging(
        logging.INFO,
        logging.DEBUG,
        log_file=cfg.log_file,
        logger=logging.getLogger(),
    )
    main(cfg)
