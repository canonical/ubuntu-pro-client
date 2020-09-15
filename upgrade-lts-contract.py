#!/usr/bin/env python3

import logging
import re

from uaclient.cli import setup_logging
from uaclient.config import UAConfig
from uaclient.contract import process_entitlements_delta
from uaclient.util import parse_os_release

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


setup_logging(logging.INFO, logging.DEBUG)
os_release = parse_os_release()

current_version = os_release["VERSION_ID"]
current_release = version_to_codename[current_version]
past_release = current_codename_to_past_codename[current_release]

past_entitlements = UAConfig(series=past_release).entitlements
new_entitlements = UAConfig(series=current_release).entitlements

process_entitlements_delta(
    past_entitlements=past_entitlements,
    new_entitlements=new_entitlements,
    allow_enable=True,
    series_overrides=False,
)
