"""
This is called in postinst when upgrading from a version <27.14
This removes the "ua_config" sub-document from uaclient.conf and moves it to
it's own json file in /var/lib/ubuntu-advantage/user-config.json.
The fields under "ua_config" are intended to be set/unset by the user via the
`pro config set` command, so we don't want them covered as a "conffile".
It writes back a uaclient.conf that will match the new default uaclient.conf
as long as no defaults have changed.
We print warning messages if errors occur with instructions to help the user
resolve them.
"""

import json
import os
import sys

from uaclient import defaults, messages
from uaclient.yaml import safe_dump, safe_load

UACLIENT_CONF_BACKUP_PATH = (
    "/etc/ubuntu-advantage/uaclient.conf.preinst-backup"
)
UACLIENT_CONF_MIGRATED_TEMP_PATH = (
    "/etc/ubuntu-advantage/uaclient.conf.preinst-backup-migrated-temp"
)

USER_CONFIG_DEFAULTS = {
    "http_proxy": None,
    "https_proxy": None,
    "apt_http_proxy": None,
    "apt_https_proxy": None,
    "ua_apt_http_proxy": None,
    "ua_apt_https_proxy": None,
    "global_apt_http_proxy": None,
    "global_apt_https_proxy": None,
    "update_messaging_timer": 21600,
    "metering_timer": 14400,
    "apt_news": True,
    "apt_news_url": "https://motd.ubuntu.com/aptnews.json",
}


def load_pre_upgrade_conf():
    # Step 1: Load pre-upgrade uaclient.conf backed up in preinst
    try:
        with open(UACLIENT_CONF_BACKUP_PATH, "r") as uaclient_conf_file:
            old_uaclient_conf = safe_load(uaclient_conf_file)
    except Exception:
        print(
            messages.USER_CONFIG_MIGRATION_WARNING_UACLIENT_CONF_LOAD,
            file=sys.stderr,
        )
        return None
    return old_uaclient_conf


def create_new_user_config_file(old_uaclient_conf):
    # Step 2: Create new user_config.json
    old_user_config = old_uaclient_conf.get("ua_config", {})
    if not isinstance(old_user_config, dict):
        # invalid and could not have been working, just ignore by treating
        # as empty
        old_user_config = {}

    new_user_config = {}
    # only keep a setting if it was changed
    for field in USER_CONFIG_DEFAULTS.keys():
        old_val = old_user_config.get(field)
        if old_val is not None and old_val != USER_CONFIG_DEFAULTS.get(field):
            new_user_config[field] = old_val

    try:
        with open(
            defaults.DEFAULT_USER_CONFIG_JSON_FILE, "w"
        ) as user_config_file:
            json.dump(new_user_config, user_config_file)
    except Exception:
        if len(new_user_config) > 0:
            print(
                messages.USER_CONFIG_MIGRATION_WARNING_NEW_USER_CONFIG_WRITE,
                file=sys.stderr,
            )
            for field in sorted(new_user_config.keys()):
                print(
                    "           pro config set {}={}".format(
                        field, new_user_config[field]
                    ),
                    file=sys.stderr,
                )


def create_new_uaclient_conffile(old_uaclient_conf):
    # Step 3: Create new uaclient.conf
    # The goal here is to end up with a minimal diff compared to the default
    # uaclient.conf.
    # If nothing has changed in any of the uaclient.conf fields, then the
    # result should exactly match the new default uaclient.conf.
    new_uaclient_conf = {
        "contract_url": old_uaclient_conf.get(
            "contract_url", defaults.BASE_CONTRACT_URL
        ),
        "log_level": old_uaclient_conf.get("log_level", "debug"),
    }

    # these are only present if they were added by the user
    for field in ("features", "settings_overrides"):
        if field in old_uaclient_conf:
            new_uaclient_conf[field] = old_uaclient_conf.get(field)

    # the rest only if they're different from defaults
    for field in (
        "data_dir",
        "log_file",
        "security_url",
    ):
        old_val = old_uaclient_conf.get(field)
        if old_val is not None and old_val != defaults.CONFIG_DEFAULTS.get(
            field
        ):
            new_uaclient_conf[field] = old_val

    try:
        print(messages.USER_CONFIG_MIGRATION_MIGRATING, file=sys.stderr)
        new_uaclient_conf_str = safe_dump(
            new_uaclient_conf,
            default_flow_style=False,
        )
        # don't open until after successful yaml serialization
        # this way, if there is an error in yaml serialization we won't
        # accidentally truncate the file
        with open(UACLIENT_CONF_MIGRATED_TEMP_PATH, "w") as uaclient_conf_file:
            uaclient_conf_file.write(new_uaclient_conf_str)

        # write to a temp file and rename atomically to avoid partial writes
        os.rename(UACLIENT_CONF_MIGRATED_TEMP_PATH, UACLIENT_CONF_BACKUP_PATH)
    except Exception:
        print(
            messages.USER_CONFIG_MIGRATION_WARNING_NEW_UACLIENT_CONF_WRITE,
            file=sys.stderr,
        )
        for field in sorted(new_uaclient_conf.keys()):
            print(
                "           {}: {}".format(
                    field, repr(new_uaclient_conf[field])
                ),
                file=sys.stderr,
            )


def main():
    old_uaclient_conf = load_pre_upgrade_conf()
    if old_uaclient_conf is None:
        # something went wrong, we can't continue migration
        return
    create_new_user_config_file(old_uaclient_conf)
    create_new_uaclient_conffile(old_uaclient_conf)


if __name__ == "__main__":
    main()
