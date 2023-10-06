#!/usr/bin/python3

from datetime import datetime, timedelta, timezone

from uaclient import apt, log
from uaclient.apt_news import update_apt_news
from uaclient.config import UAConfig


def main(cfg: UAConfig):
    if not cfg.apt_news:
        return

    last_update = apt.get_apt_cache_datetime()
    one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    if last_update is not None and last_update > one_day_ago:
        return

    update_apt_news(cfg)


if __name__ == "__main__":
    log.setup_journald_logging()
    cfg = UAConfig()
    main(cfg)
