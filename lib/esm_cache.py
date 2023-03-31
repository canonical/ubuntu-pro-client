#!/usr/bin/env python3

import logging

from uaclient import defaults
from uaclient.apt import update_esm_caches
from uaclient.config import UAConfig
from uaclient.daemon import setup_logging

LOG = logging.getLogger("uaclient.lib.esm_cache")
root_logger = logging.getLogger("uaclient")


def main(cfg: UAConfig) -> None:
    try:
        update_esm_caches(cfg)
    except Exception as e:
        msg = getattr(e, "msg", str(e))
        LOG.error("Error updating the cache: %s", msg)


if __name__ == "__main__":
    root_logger.propagate = False
    setup_logging(
        logging.INFO,
        logging.DEBUG,
        defaults.CONFIG_DEFAULTS["log_file"],
        logger=root_logger,
    )
    cfg = UAConfig()
    setup_logging(
        logging.INFO,
        logging.DEBUG,
        log_file=cfg.log_file,
        logger=root_logger,
    )
    main(cfg)
