#!/usr/bin/env python3

"""
This script should be used after running do-release-upgrade in a machine.
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
import sys
import time

from uaclient.cli import setup_logging
from uaclient.config import UAConfig
from uaclient.contract import process_entitlements_delta
from uaclient.util import parse_os_release, subp

version_to_codename = {
    "14.04": "trusty",
    "16.04": "xenial",
    "18.04": "bionic",
    "20.04": "focal",
    "21.10": "impish",
    "22.04": "jammy",
}

current_codename_to_past_codename = {
    "xenial": "trusty",
    "bionic": "xenial",
    "focal": "bionic",
    "impish": "focal",
    # We are considering the past release for Jammy to be Focal
    # because we don't have any services available on Impish.
    # Therefore, it is safer for us to try to process contract deltas
    # using Focal
    "jammy": "focal",
}


def process_contract_delta_after_apt_lock() -> None:
    logging.debug("Check whether to upgrade-lts-contract")
    if not UAConfig().is_attached:
        logging.debug("Skipping upgrade-lts-contract. Machine is unattached")
        return
    out, _err = subp(["lsof", "/var/lib/apt/lists/lock"], rcs=[0, 1])
    msg = "Starting upgrade-lts-contract."
    if out:
        msg += " Retrying every 10 seconds waiting on released apt lock"
    print(msg)
    logging.debug(msg)

    current_version = parse_os_release()["VERSION_ID"]
    current_release = version_to_codename.get(current_version)

    if current_release is None:
        msg = "Unable to get release codename for version: {}".format(
            current_version
        )
        print(msg)
        logging.warning(msg)
        sys.exit(1)

    if current_release == "trusty":
        msg = "Unable to execute upgrade-lts-contract.py on trusty"
        print(msg)
        logging.warning(msg)
        sys.exit(1)

    past_release = current_codename_to_past_codename.get(current_release)
    if past_release is None:
        msg = "Could not find past release for: {}".format(current_release)
        print(msg)
        logging.warning(msg)
        sys.exit(1)

    past_entitlements = UAConfig(series=past_release).entitlements
    new_entitlements = UAConfig(series=current_release).entitlements

    retry_count = 0
    while out:
        # Loop until apt hold is released at the end of `do-release-upgrade`
        time.sleep(10)
        out, _err = subp(["lsof", "/var/lib/apt/lists/lock"], rcs=[0, 1])
        retry_count += 1

    msg = "upgrade-lts-contract processing contract deltas: {} -> {}".format(
        past_release, current_release
    )
    print(msg)
    logging.debug(msg)

    process_entitlements_delta(
        past_entitlements=past_entitlements,
        new_entitlements=new_entitlements,
        allow_enable=True,
        series_overrides=False,
    )
    msg = "upgrade-lts-contract succeeded after {} retries".format(retry_count)
    print(msg)
    logging.debug(msg)


if __name__ == "__main__":
    setup_logging(logging.INFO, logging.DEBUG)
    process_contract_delta_after_apt_lock()
