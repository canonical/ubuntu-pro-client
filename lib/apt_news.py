#!/usr/bin/python3

import logging
from datetime import datetime, timedelta, timezone

from uaclient import apt, defaults
from uaclient.apt_news import update_apt_news
from uaclient.config import UAConfig
from uaclient.daemon import setup_logging


def main(cfg: UAConfig):
    if not cfg.apt_news:
        return

    last_update = apt.get_apt_cache_datetime()
    one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    if last_update is not None and last_update > one_day_ago:
        return

    update_apt_news(cfg)


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
