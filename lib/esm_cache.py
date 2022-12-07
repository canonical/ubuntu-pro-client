#!/usr/bin/env python3

import logging

from uaclient.apt import update_esm_caches
from uaclient.config import UAConfig
from uaclient.daemon import setup_logging


def main(cfg: UAConfig) -> None:
    update_esm_caches(cfg)


if __name__ == "__main__":
    cfg = UAConfig(root_mode=True)
    setup_logging(
        logging.INFO,
        logging.DEBUG,
        log_file=cfg.log_file,
        logger=logging.getLogger(),
    )
    main(cfg)
