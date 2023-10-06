#!/usr/bin/env python3

import logging

from uaclient import log
from uaclient.apt import update_esm_caches
from uaclient.config import UAConfig

LOG = logging.getLogger("ubuntupro.lib.esm_cache")


def main(cfg: UAConfig) -> None:
    try:
        update_esm_caches(cfg)
    except Exception as e:
        msg = getattr(e, "msg", str(e))
        LOG.error("Error updating the cache: %s", msg)


if __name__ == "__main__":
    log.setup_journald_logging()
    cfg = UAConfig()
    main(cfg)
