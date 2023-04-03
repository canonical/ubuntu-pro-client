#!/usr/bin/env python3

"""
This script is called after running do-release-upgrade in a machine.
See uaclient/upgrade_lts_contract.py for more details.
"""

import logging

from uaclient import upgrade_lts_contract
from uaclient.cli import setup_logging
from uaclient.config import UAConfig

if __name__ == "__main__":
    setup_logging(logging.INFO, logging.DEBUG)
    cfg = UAConfig()
    upgrade_lts_contract.process_contract_delta_after_apt_lock(cfg)
    upgrade_lts_contract.remove_private_esm_apt_cache()
