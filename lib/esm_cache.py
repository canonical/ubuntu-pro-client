#!/usr/bin/env python3

import logging

from uaclient import defaults
from uaclient.apt import update_esm_caches
from uaclient.config import UAConfig
from uaclient.daemon import setup_logging

LOG = logging.getLogger("ubuntupro.lib.esm_cache")


def main(cfg: UAConfig) -> None:
    try:
        update_esm_caches(cfg)
    except Exception as e:
        msg = getattr(e, "msg", str(e))
        LOG.error("Error updating the cache: %s", msg)


if __name__ == "__main__":
    setup_logging(
        logging.INFO,
        logging.DEBUG,
        defaults.CONFIG_DEFAULTS["log_file"],
    )
    cfg = UAConfig()
    setup_logging(
        logging.INFO,
        logging.DEBUG,
        cfg.log_file,
    )
    main(cfg)
