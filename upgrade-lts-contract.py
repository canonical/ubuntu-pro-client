#!/usr/bin/env python3

import argparse
import contextlib
import logging
import os

try:
    from daemon import DaemonContext
except ImportError:
    DaemonContext = contextlib.suppress()

from uaclient.cli import setup_logging
from uaclient.config import UAConfig
from uaclient.contract import process_entitlements_delta
from uaclient.util import parse_os_release, subp

version_to_codename = {
    "14.04": "trusty",
    "16.04": "xenial",
    "18.04": "bionic",
    "20.04": "focal",
}

current_codename_to_past_codename = {
    "xenial": "trusty",
    "bionic": "xenial",
    "focal": "bionic",
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-daemon",
        action="store_true",
        help=("Sets the script to not run on daemon mode"),
    )

    return parser.parse_args()


def process_contract_delta_after_apt_lock():
    setup_logging(logging.INFO, logging.DEBUG)
    out, _err = subp(["lsof", "/var/lib/apt/lists/lock"], rcs=[0, 1])
    msg = "Starting upgrade-lts-contract."
    if out:
        mgs += " Retrying every 10 seconds waiting on released apt lock"
    print(msg)
    logging.debug(msg)

    current_version = parse_os_release()["VERSION_ID"]
    current_release = version_to_codename[current_version]
    past_release = current_codename_to_past_codename[current_release]

    past_entitlements = UAConfig(series=past_release).entitlements
    new_entitlements = UAConfig(series=current_release).entitlements

    retry_count = 0
    while out:
        time.sleep(10)
        out, _err = subp(["lsof", "/var/lib/apt/lists/lock"], rcs=[0, 1])
        retry_count += 1
    logging.debug(
        "upgrade-lts-contract processing contract deltas: %s -> %s",
        past_release,
        current_release,
    )

    process_entitlements_delta(
        past_entitlements=past_entitlements,
        new_entitlements=new_entitlements,
        allow_enable=True,
        series_overrides=False,
    )
    logging.debug(
        "upgrade-lts-contract succeeded after %d retries", retry_count
    )

    os.remove("/etc/ubuntu-advantage/request-update-contract")


if __name__ == "__main__":
    args = parse_args()

    if args.no_daemon:
        process_contract_delta_after_apt_lock()
    else:
        with DaemonContext():
            process_contract_delta_after_apt_lock()
