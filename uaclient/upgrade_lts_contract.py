#!/usr/bin/env python3

"""
This function is called from lib/upgrade_lts_contract.py and from
lib/reboot_cmds.py

This function should be used after running do-release-upgrade in a machine.
It will detect any contract deltas between the release before
do-release-upgrade and the current release. If we find any differences in
the uaclient contract between those releases, we will apply that difference
in the upgraded release.

For example, suppose we are on Trusty and we are upgrading to Xenial. We found
that the apt url for esm services on trusty:

https://esm.ubuntu.com/ubuntu

While on Xenial, the apt url is:

https://esm.ubuntu.com/infra/ubuntu

This script will detect differences like that and update the Xenial system
to reflect them.
"""

import logging
import time

from uaclient import defaults, exceptions, messages, system, util
from uaclient.api import ProgressWrapper
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.config import UAConfig
from uaclient.entitlements import (
    entitlement_factory,
    entitlements_enable_order,
)
from uaclient.entitlements.entitlement_status import (
    ApplicabilityStatus,
    ApplicationStatus,
)

# We consider the past release for LTSs to be the last LTS,
# because we don't have any services available on non-LTS.
# This makes it safer for us to try to process contract deltas.
# For example, we had "jammy": "focal" even when Impish was
# still supported.
current_codename_to_past_codename = {
    "xenial": "trusty",
    "bionic": "xenial",
    "focal": "bionic",
    "jammy": "focal",
    "noble": "jammy",
    "oracular": "noble",
}

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


def process_contract_delta_after_apt_lock(cfg: UAConfig) -> None:
    LOG.debug("Check whether to upgrade-lts-contract")
    if not _is_attached(cfg).is_attached:
        LOG.debug("Skipping upgrade-lts-contract. Machine is unattached")
        return
    LOG.debug("Starting upgrade-lts-contract.")
    out, _err = system.subp(["lsof", "/var/lib/apt/lists/lock"], rcs=[0, 1])
    if out:
        print(messages.RELEASE_UPGRADE_APT_LOCK_HELD_WILL_WAIT)

    print(messages.RELEASE_UPGRADE_STARTING)
    for name in entitlements_enable_order(cfg):
        try:
            entitlement = entitlement_factory(
                cfg=cfg,
                name=name,
                variant="",
            )
        except exceptions.EntitlementNotFoundError:
            LOG.debug("entitlement not found: %s", name)

        application_status, _ = entitlement.application_status()
        applicability_status, _ = entitlement.applicability_status()

        if (
            application_status == ApplicationStatus.ENABLED
            and applicability_status == ApplicabilityStatus.INAPPLICABLE
        ):
            retry_count = 0
            while out:
                # Loop until apt hold is released at the end of `do-release-upgrade`  # noqa
                LOG.debug(
                    "Detected that apt lock is held. Sleeping 10 seconds."
                )
                time.sleep(10)
                out, _err = system.subp(
                    ["lsof", "/var/lib/apt/lists/lock"], rcs=[0, 1]
                )
                retry_count += 1

            LOG.debug("upgrade-lts-contract disabling %s", name)
            ret = entitlement._perform_disable(progress=ProgressWrapper())

            if not ret:
                LOG.debug("upgrade-lts-contract failed disabling %s", name)

    print(messages.RELEASE_UPGRADE_SUCCESS)


def remove_private_esm_apt_cache():
    system.ensure_folder_absent(defaults.ESM_APT_ROOTDIR)
