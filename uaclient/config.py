import copy
import logging
import os
from functools import lru_cache, wraps
from typing import Any, Dict, Optional

from uaclient import (
    apt,
    event_logger,
    exceptions,
    http,
    messages,
    snap,
    system,
    util,
)
from uaclient.defaults import (
    APT_NEWS_URL,
    BASE_CONTRACT_URL,
    BASE_LIVEPATCH_URL,
    BASE_SECURITY_URL,
    CONFIG_DEFAULTS,
    CONFIG_FIELD_ENVVAR_ALLOWLIST,
    DEFAULT_CONFIG_FILE,
    DEFAULT_DATA_DIR,
)
from uaclient.files import user_config_file
from uaclient.yaml import safe_load

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))

MERGE_ID_KEY_MAP = {
    "availableResources": "name",
    "resourceEntitlements": "type",
}
UNSET_SETTINGS_OVERRIDE_KEY = "_unset"

# Keys visible and configurable using `pro config set|unset|show` subcommands
UA_CONFIGURABLE_KEYS = (
    "http_proxy",
    "https_proxy",
    "apt_http_proxy",
    "apt_https_proxy",
    "ua_apt_http_proxy",
    "ua_apt_https_proxy",
    "global_apt_http_proxy",
    "global_apt_https_proxy",
    "update_messaging_timer",
    "metering_timer",
    "apt_news",
    "apt_news_url",
)

# Basic schema validation top-level keys for parse_config handling
VALID_UA_CONFIG_KEYS = (
    "contract_url",
    "data_dir",
    "features",
    "log_file",
    "log_level",
    "security_url",
    "settings_overrides",
    "ua_config",
    "livepatch_url",
)


event = event_logger.get_event_logger()


class UAConfig:
    ua_scoped_proxy_options = ("ua_apt_http_proxy", "ua_apt_https_proxy")
    global_scoped_proxy_options = (
        "global_apt_http_proxy",
        "global_apt_https_proxy",
    )
    deprecated_global_scoped_proxy_options = (
        "apt_http_proxy",
        "apt_https_proxy",
    )

    def __init__(
        self,
        cfg: Optional[Dict[str, Any]] = None,
        user_config: Optional[user_config_file.UserConfigData] = None,
        series: Optional[str] = None,
    ) -> None:
        """"""
        if cfg:
            self.cfg_path = None
            self.cfg = cfg
            self.invalid_keys = None
        else:
            self.cfg_path = get_config_path()
            self.cfg, self.invalid_keys = parse_config(self.cfg_path)

        if user_config:
            self.user_config = user_config
        else:
            try:
                self.user_config = user_config_file.user_config.read()
            except Exception as e:
                LOG.warning("Error loading user config", exc_info=e)
                LOG.warning("Using default config values")
                self.user_config = user_config_file.UserConfigData()

        # support old ua_config values in uaclient.conf as user-config.json
        # value overrides
        if "ua_config" in self.cfg:
            self.user_config = user_config_file.UserConfigData.from_dict(
                {**self.user_config.to_dict(), **self.cfg["ua_config"]},
                optional_type_errors_become_null=True,
            )

        self.series = series

    @property
    def contract_url(self) -> str:
        return self.cfg.get("contract_url", BASE_CONTRACT_URL)

    @property
    def security_url(self) -> str:
        return self.cfg.get("security_url", BASE_SECURITY_URL)

    @property
    def livepatch_url(self) -> str:
        return self.cfg.get("livepatch_url", BASE_LIVEPATCH_URL)

    @property
    def http_proxy(self) -> Optional[str]:
        return self.user_config.http_proxy

    @http_proxy.setter
    def http_proxy(self, value: str):
        self.user_config.http_proxy = value
        user_config_file.user_config.write(self.user_config)

    @property
    def https_proxy(self) -> Optional[str]:
        return self.user_config.https_proxy

    @https_proxy.setter
    def https_proxy(self, value: str):
        self.user_config.https_proxy = value
        user_config_file.user_config.write(self.user_config)

    @property
    def ua_apt_https_proxy(self) -> Optional[str]:
        return self.user_config.ua_apt_https_proxy

    @ua_apt_https_proxy.setter
    def ua_apt_https_proxy(self, value: str):
        self.user_config.ua_apt_https_proxy = value
        user_config_file.user_config.write(self.user_config)

    @property
    def ua_apt_http_proxy(self) -> Optional[str]:
        return self.user_config.ua_apt_http_proxy

    @ua_apt_http_proxy.setter
    def ua_apt_http_proxy(self, value: str):
        self.user_config.ua_apt_http_proxy = value
        user_config_file.user_config.write(self.user_config)

    @property  # type: ignore
    @lru_cache(maxsize=None)
    def global_apt_http_proxy(self) -> Optional[str]:
        global_val = self.user_config.global_apt_http_proxy
        if global_val:
            return global_val

        old_apt_val = self.user_config.apt_http_proxy
        if old_apt_val:
            event.info(
                messages.WARNING_DEPRECATED_FIELD.format(
                    old="apt_http_proxy", new="global_apt_http_proxy"
                )
            )
            return old_apt_val
        return None

    @global_apt_http_proxy.setter
    def global_apt_http_proxy(self, value: str):
        self.user_config.global_apt_http_proxy = value
        self.user_config.apt_http_proxy = None
        UAConfig.global_apt_http_proxy.fget.cache_clear()  # type: ignore
        user_config_file.user_config.write(self.user_config)

    @property  # type: ignore
    @lru_cache(maxsize=None)
    def global_apt_https_proxy(self) -> Optional[str]:
        global_val = self.user_config.global_apt_https_proxy
        if global_val:
            return global_val

        old_apt_val = self.user_config.apt_https_proxy
        if old_apt_val:
            event.info(
                messages.WARNING_DEPRECATED_FIELD.format(
                    old="apt_https_proxy", new="global_apt_https_proxy"
                )
            )
            return old_apt_val
        return None

    @global_apt_https_proxy.setter
    def global_apt_https_proxy(self, value: str):
        self.user_config.global_apt_https_proxy = value
        self.user_config.apt_https_proxy = None
        UAConfig.global_apt_https_proxy.fget.cache_clear()  # type: ignore
        user_config_file.user_config.write(self.user_config)

    @property
    def update_messaging_timer(self) -> int:
        val = self.user_config.update_messaging_timer
        if val is None:
            return 21600
        return val

    @update_messaging_timer.setter
    def update_messaging_timer(self, value: int):
        self.user_config.update_messaging_timer = value
        user_config_file.user_config.write(self.user_config)

    @property
    def metering_timer(self) -> int:
        val = self.user_config.metering_timer
        if val is None:
            return 14400
        return val

    @metering_timer.setter
    def metering_timer(self, value: int):
        self.user_config.metering_timer = value
        user_config_file.user_config.write(self.user_config)

    @property
    def poll_for_pro_license(self) -> bool:
        # TODO: when polling is supported
        #     1. change default here to True
        #     2. add this field to UA_CONFIGURABLE_KEYS
        val = self.user_config.poll_for_pro_license
        if val is None:
            return False
        return val

    @poll_for_pro_license.setter
    def poll_for_pro_license(self, value: bool):
        self.user_config.poll_for_pro_license = value
        user_config_file.user_config.write(self.user_config)

    @property
    def polling_error_retry_delay(self) -> int:
        # TODO: when polling is supported
        #     1. add this field to UA_CONFIGURABLE_KEYS
        val = self.user_config.polling_error_retry_delay
        if val is None:
            return 600
        return val

    @polling_error_retry_delay.setter
    def polling_error_retry_delay(self, value: int):
        self.user_config.polling_error_retry_delay = value
        user_config_file.user_config.write(self.user_config)

    @property
    def apt_news(self) -> bool:
        val = self.user_config.apt_news
        if val is None:
            return True
        return val

    @apt_news.setter
    def apt_news(self, value: bool):
        self.user_config.apt_news = value
        user_config_file.user_config.write(self.user_config)

    @property
    def apt_news_url(self) -> str:
        val = self.user_config.apt_news_url
        if val is None:
            return APT_NEWS_URL
        return val

    @apt_news_url.setter
    def apt_news_url(self, value: str):
        self.user_config.apt_news_url = value
        user_config_file.user_config.write(self.user_config)

    @property
    def data_dir(self):
        return self.cfg.get("data_dir", DEFAULT_DATA_DIR)

    @property
    def log_level(self):
        log_level = self.cfg.get("log_level", "DEBUG")
        try:
            return getattr(logging, log_level.upper())
        except AttributeError:
            return logging.DEBUG

    @property
    def log_file(self) -> str:
        return self.cfg.get("log_file", CONFIG_DEFAULTS["log_file"])

    @property
    def features(self):
        """Return a dictionary of any features provided in uaclient.conf."""
        features = self.cfg.get("features")
        if features:
            if isinstance(features, dict):
                return features
            else:
                LOG.warning(
                    "Unexpected uaclient.conf features value."
                    " Expected dict, but found %s",
                    features,
                )
        return {}

    def process_config(self):
        for prop in (
            "update_messaging_timer",
            "metering_timer",
        ):
            value = getattr(self, prop)
            if value is None:
                LOG.debug(
                    "No config set for %s, default value will be used.", prop
                )
            elif not isinstance(value, int) or value < 0:
                raise exceptions.InvalidPosIntConfigValue(
                    key=prop, value=value
                )

        if (self.global_apt_http_proxy or self.global_apt_https_proxy) and (
            self.ua_apt_http_proxy or self.ua_apt_https_proxy
        ):
            # Should we unset the config values?
            raise exceptions.InvalidProxyCombinationConfig()

        http.validate_proxy(
            "http",
            self.global_apt_http_proxy,
            http.PROXY_VALIDATION_APT_HTTP_URL,
        )
        http.validate_proxy(
            "https",
            self.global_apt_https_proxy,
            http.PROXY_VALIDATION_APT_HTTPS_URL,
        )
        http.validate_proxy(
            "http", self.ua_apt_http_proxy, http.PROXY_VALIDATION_APT_HTTP_URL
        )
        http.validate_proxy(
            "https",
            self.ua_apt_https_proxy,
            http.PROXY_VALIDATION_APT_HTTPS_URL,
        )
        http.validate_proxy(
            "http", self.http_proxy, http.PROXY_VALIDATION_SNAP_HTTP_URL
        )
        http.validate_proxy(
            "https", self.https_proxy, http.PROXY_VALIDATION_SNAP_HTTPS_URL
        )

        if self.global_apt_http_proxy or self.global_apt_https_proxy:
            apt.setup_apt_proxy(
                self.global_apt_http_proxy,
                self.global_apt_https_proxy,
                apt.AptProxyScope.GLOBAL,
            )
        elif self.ua_apt_http_proxy or self.ua_apt_https_proxy:
            apt.setup_apt_proxy(
                self.ua_apt_http_proxy,
                self.ua_apt_https_proxy,
                apt.AptProxyScope.UACLIENT,
            )

        services_with_proxies = []
        if snap.is_snapd_installed():
            snap.configure_snap_proxy(self.http_proxy, self.https_proxy)
            if (
                not self.http_proxy
                and snap.get_config_option_value(snap.HTTP_PROXY_OPTION)
            ) or (
                not self.https_proxy
                and snap.get_config_option_value(snap.HTTPS_PROXY_OPTION)
            ):
                services_with_proxies.append("snap")

        from uaclient import livepatch
        from uaclient.api.u.pro.status.enabled_services.v1 import (
            _enabled_services,
        )

        enabled_services = _enabled_services(self).enabled_services
        livepatch_enabled = any(
            ent for ent in enabled_services if ent.name == "livepatch"
        )

        if livepatch_enabled:
            livepatch.configure_livepatch_proxy(
                self.http_proxy, self.https_proxy
            )
            if (
                not self.http_proxy
                and livepatch.get_config_option_value(
                    livepatch.HTTP_PROXY_OPTION
                )
            ) or (
                not self.https_proxy
                and livepatch.get_config_option_value(
                    livepatch.HTTPS_PROXY_OPTION
                )
            ):
                services_with_proxies.append("livepatch")

        if len(services_with_proxies) > 0:
            services = ", ".join(services_with_proxies)
            print(
                messages.PROXY_DETECTED_BUT_NOT_CONFIGURED.format(
                    services=services
                )
            )

    def warn_about_invalid_keys(self):
        if self.invalid_keys is not None:
            for invalid_key in sorted(self.invalid_keys):
                LOG.warning(
                    "Ignoring invalid uaclient.conf key: %s", invalid_key
                )
        if "ua_config" in self.cfg:
            # this one is still technically supported but we want people to
            # migrate so it gets a special warning
            LOG.warning('legacy "ua_config" found in uaclient.conf')
            LOG.warning("Please do the following:")
            LOG.warning(
                "  1. run `sudo pro config set field=value` for each"
                ' field/value pair present under "ua_config" in'
                " /etc/ubuntu-advantage/uaclient.conf"
            )
            LOG.warning(
                '  2. Delete "ua_config" and all sub-fields in'
                " /etc/ubuntu-advantage/uaclient.conf"
            )


def get_config_path() -> str:
    """Get config path to be used when loading config dict."""
    config_file = os.environ.get("UA_CONFIG_FILE")
    if config_file:
        return config_file

    return DEFAULT_CONFIG_FILE


def parse_config(config_path=None):
    """Parse known Pro config file

    Attempt to find configuration in cwd and fallback to DEFAULT_CONFIG_FILE.
    Any missing configuration keys will be set to CONFIG_DEFAULTS.

    Values are overridden by any environment variable with prefix 'UA_'.

    @param config_path: Fullpath to pro configfile. If unspecified, use
        DEFAULT_CONFIG_FILE.

    @return: Dict of configuration values.
    """
    cfg = copy.copy(CONFIG_DEFAULTS)  # type: Dict[str, Any]

    if not config_path:
        config_path = get_config_path()

    LOG.debug("Using client configuration file at %s", config_path)
    if os.path.exists(config_path):
        cfg.update(safe_load(system.load_file(config_path)))
    env_keys = {}
    for key, value in os.environ.items():
        key = key.lower()
        if key.startswith("ua_"):
            # Strip leading UA_
            field_name = key[3:]
            if field_name.startswith("features_"):
                # Strip leading UA_FEATURES_
                feature_field_name = field_name[9:]

                # Users can provide a yaml file to override
                # config behavor. If they do, we are going
                # to load that yaml and update the config
                # with it
                if value.endswith("yaml"):
                    if os.path.exists(value):
                        value = safe_load(system.load_file(value))
                    else:
                        raise exceptions.InvalidFeatureYamlConfigValue(
                            filepath=value
                        )

                if "features" not in cfg:
                    cfg["features"] = {feature_field_name: value}
                else:
                    cfg["features"][feature_field_name] = value
            elif key in CONFIG_FIELD_ENVVAR_ALLOWLIST:
                env_keys[field_name] = value
    cfg.update(env_keys)
    if "data_dir" in cfg:
        cfg["data_dir"] = os.path.expanduser(cfg["data_dir"])
    for key in ("contract_url", "security_url"):
        if not http.is_service_url(cfg[key]):
            raise exceptions.InvalidURLConfigValue(key=key, value=cfg[key])

    invalid_keys = set(cfg.keys()).difference(VALID_UA_CONFIG_KEYS)
    for invalid_key in invalid_keys:
        cfg.pop(invalid_key)

    return cfg, invalid_keys


def apply_config_settings_override(override_key: str):
    """Decorator used to override function return by config settings.

    To identify if we should override the function return, we check
    if the config object has the expected override key, we use it
    has, we will use the key value as the function return. Otherwise
    we will call the function normally.

    @param override_key: key to be looked for in the settings_override
     entry in the config dict. If that key is present, we will return
     its value as the function return.
    """

    def wrapper(f):
        @wraps(f)
        def new_f():
            cfg, _ = parse_config()
            value_override = cfg.get("settings_overrides", {}).get(
                override_key, UNSET_SETTINGS_OVERRIDE_KEY
            )

            if value_override != UNSET_SETTINGS_OVERRIDE_KEY:
                if override_key == "cloud_type":
                    return (value_override, None)
                return value_override

            return f()

        return new_f

    return wrapper
