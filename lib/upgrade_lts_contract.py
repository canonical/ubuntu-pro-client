#!/usr/bin/env python3

"""
This script is called after running do-release-upgrade in a machine.
See uaclient/upgrade_lts_contract.py for more details.
"""

import logging

from uaclient import config, defaults, http, log, upgrade_lts_contract
from uaclient.timer import update_contract_info

if __name__ == "__main__":
    log.setup_cli_logging(logging.DEBUG, defaults.CONFIG_DEFAULTS["log_level"])
    cfg = config.UAConfig()
    log.setup_cli_logging(cfg.log_level, cfg.log_file)
    http.configure_web_proxy(cfg.http_proxy, cfg.https_proxy)
    update_contract_info.validate_release_series(cfg, show_message=True)
    upgrade_lts_contract.process_contract_delta_after_apt_lock(cfg)
    upgrade_lts_contract.remove_private_esm_apt_cache()
