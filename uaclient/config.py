import copy
import json
import logging
import os
import re
from collections import namedtuple
from datetime import datetime
from functools import lru_cache, wraps
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar

import yaml

from uaclient import apt, event_logger, exceptions, messages, snap, util
from uaclient.defaults import (
    BASE_CONTRACT_URL,
    BASE_SECURITY_URL,
    CONFIG_DEFAULTS,
    CONFIG_FIELD_ENVVAR_ALLOWLIST,
    DEFAULT_CONFIG_FILE,
)

LOG = logging.getLogger(__name__)

PRIVATE_SUBDIR = "private"
MERGE_ID_KEY_MAP = {
    "availableResources": "name",
    "resourceEntitlements": "type",
}
UNSET_SETTINGS_OVERRIDE_KEY = "_unset"

# Keys visible and configurable using `ua config set|unset|show` subcommands
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
    "update_status_timer",
    "metering_timer",
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
    "timer_log_file",
    "daemon_log_file",
    "ua_config",
)

# A data path is a filename, an attribute ("private") indicating whether it
# should only be readable by root, and an attribute ("permanent") indicating
# whether it should stick around even when detached.
DataPath = namedtuple("DataPath", ("filename", "private", "permanent"))

event = event_logger.get_event_logger()

# needed for solving mypy errors dealing with _lru_cache_wrapper
# Found at https://github.com/python/mypy/issues/5858#issuecomment-454144705
S = TypeVar("S", bound=str)


def str_cache(func: Callable[..., S]) -> S:
    return lru_cache()(func)  # type: ignore


class UAConfig:

    data_paths = {
        "instance-id": DataPath("instance-id", True, False),
        "machine-access-cis": DataPath("machine-access-cis.json", True, False),
        "machine-token": DataPath("machine-token.json", True, False),
        "lock": DataPath("lock", True, False),
        "status-cache": DataPath("status.json", False, False),
        "notices": DataPath("notices.json", False, False),
        "marker-reboot-cmds": DataPath(
            "marker-reboot-cmds-required", False, False
        ),
        "services-once-enabled": DataPath(
            "services-once-enabled", False, True
        ),
        "jobs-status": DataPath("jobs-status.json", False, True),
    }  # type: Dict[str, DataPath]

    _entitlements = None  # caching to avoid repetitive file reads
    _machine_token = None  # caching to avoid repetitive file reading
    _contract_expiry_datetime = None
    ua_scoped_proxy_options = ("ua_apt_http_proxy", "ua_apt_https_proxy")
    global_scoped_proxy_options = (
        "global_apt_http_proxy",
        "global_apt_https_proxy",
    )
    deprecated_global_scoped_proxy_options = (
        "apt_http_proxy",
        "apt_https_proxy",
    )

    def __init__(self, cfg: Dict[str, Any] = None, series: str = None) -> None:
        """"""
        if cfg:
            self.cfg_path = None
            self.cfg = cfg
            self.invalid_keys = None
        else:
            self.cfg_path = get_config_path()
            self.cfg, self.invalid_keys = parse_config(self.cfg_path)

        self.series = series

    @property
    def accounts(self):
        """Return the list of accounts that apply to this authorized user."""
        if self.is_attached:
            accountInfo = self.machine_token["machineTokenInfo"]["accountInfo"]
            return [accountInfo]
        return []

    @property
    def contract_url(self) -> str:
        return self.cfg.get("contract_url", BASE_CONTRACT_URL)

    @property
    def security_url(self) -> str:
        return self.cfg.get("security_url", BASE_SECURITY_URL)

    @property
    def http_proxy(self) -> Optional[str]:
        return self.cfg.get("ua_config", {}).get("http_proxy")

    @http_proxy.setter
    def http_proxy(self, value: str):
        if "ua_config" not in self.cfg:
            self.cfg["ua_config"] = {}
        self.cfg["ua_config"]["http_proxy"] = value
        self.write_cfg()

    @property
    def https_proxy(self) -> Optional[str]:
        return self.cfg.get("ua_config", {}).get("https_proxy")

    @https_proxy.setter
    def https_proxy(self, value: str):
        if "ua_config" not in self.cfg:
            self.cfg["ua_config"] = {}
        self.cfg["ua_config"]["https_proxy"] = value
        self.write_cfg()

    @property
    def ua_apt_https_proxy(self) -> Optional[str]:
        return self.cfg.get("ua_config", {}).get("ua_apt_https_proxy")

    @ua_apt_https_proxy.setter
    def ua_apt_https_proxy(self, value: str):
        if "ua_config" not in self.cfg:
            self.cfg["ua_config"] = {}
        self.cfg["ua_config"]["ua_apt_https_proxy"] = value
        self.write_cfg()

    @property
    def ua_apt_http_proxy(self) -> Optional[str]:
        return self.cfg.get("ua_config", {}).get("ua_apt_http_proxy")

    @ua_apt_http_proxy.setter
    def ua_apt_http_proxy(self, value: str):
        if "ua_config" not in self.cfg:
            self.cfg["ua_config"] = {}
        self.cfg["ua_config"]["ua_apt_http_proxy"] = value
        self.write_cfg()

    @property  # type: ignore
    @str_cache
    def global_apt_http_proxy(self) -> Optional[str]:
        global_val = self.cfg.get("ua_config", {}).get("global_apt_http_proxy")
        if global_val:
            return global_val

        old_apt_val = self.cfg.get("ua_config", {}).get("apt_http_proxy")
        if old_apt_val:
            event.info(messages.WARNING_DEPRECATED_APT_HTTP)
            return old_apt_val
        return None

    @global_apt_http_proxy.setter
    def global_apt_http_proxy(self, value: str):
        if "ua_config" not in self.cfg:
            self.cfg["ua_config"] = {}
        self.cfg["ua_config"]["global_apt_http_proxy"] = value
        self.cfg["ua_config"]["apt_http_proxy"] = None
        UAConfig.global_apt_http_proxy.fget.cache_clear()  # type: ignore
        self.write_cfg()

    @property  # type: ignore
    @str_cache
    def global_apt_https_proxy(self) -> Optional[str]:
        global_val = self.cfg.get("ua_config", {}).get(
            "global_apt_https_proxy"
        )
        if global_val:
            return global_val

        old_apt_val = self.cfg.get("ua_config", {}).get("apt_https_proxy")
        if old_apt_val:
            event.info(messages.WARNING_DEPRECATED_APT_HTTPS)
            return old_apt_val
        return None

    @global_apt_https_proxy.setter
    def global_apt_https_proxy(self, value: str):
        if "ua_config" not in self.cfg:
            self.cfg["ua_config"] = {}
        self.cfg["ua_config"]["global_apt_https_proxy"] = value
        self.cfg["ua_config"]["apt_https_proxy"] = None
        UAConfig.global_apt_https_proxy.fget.cache_clear()  # type: ignore
        self.write_cfg()

    @property
    def update_status_timer(self) -> Optional[int]:
        return self.cfg.get("ua_config", {}).get("update_status_timer")

    @update_status_timer.setter
    def update_status_timer(self, value: int):
        if "ua_config" not in self.cfg:
            self.cfg["ua_config"] = {}
        self.cfg["ua_config"]["update_status_timer"] = value
        self.write_cfg()

    @property
    def update_messaging_timer(self) -> Optional[int]:
        return self.cfg.get("ua_config", {}).get("update_messaging_timer")

    @update_messaging_timer.setter
    def update_messaging_timer(self, value: int):
        if "ua_config" not in self.cfg:
            self.cfg["ua_config"] = {}
        self.cfg["ua_config"]["update_messaging_timer"] = value
        self.write_cfg()

    @property
    def metering_timer(self) -> "Optional[int]":
        return self.cfg.get("ua_config", {}).get("metering_timer")

    @metering_timer.setter
    def metering_timer(self, value: int):
        if "ua_config" not in self.cfg:
            self.cfg["ua_config"] = {}
        self.cfg["ua_config"]["metering_timer"] = value
        self.write_cfg()

    @property
    def poll_for_pro_license(self) -> bool:
        # TODO: when polling is supported
        #     1. change default here to True
        #     2. add this field to UA_CONFIGURABLE_KEYS
        return self.cfg.get("ua_config", {}).get("poll_for_pro_license", False)

    @poll_for_pro_license.setter
    def poll_for_pro_license(self, value: bool):
        if "ua_config" not in self.cfg:
            self.cfg["ua_config"] = {}
        self.cfg["ua_config"]["poll_for_pro_license"] = value
        self.write_cfg()

    @property
    def polling_error_retry_delay(self) -> int:
        # TODO: when polling is supported
        #     1. add this field to UA_CONFIGURABLE_KEYS
        return self.cfg.get("ua_config", {}).get(
            "polling_error_retry_delay", 600
        )

    @polling_error_retry_delay.setter
    def polling_error_retry_delay(self, value: int):
        if "ua_config" not in self.cfg:
            self.cfg["ua_config"] = {}
        self.cfg["ua_config"]["polling_error_retry_delay"] = value
        self.write_cfg()

    def check_lock_info(self) -> Tuple[int, str]:
        """Return lock info if config lock file is present the lock is active.

        If process claiming the lock is no longer present, remove the lock file
        and log a warning.

        :param lock_path: Full path to the lock file.

        :return: A tuple (pid, string describing lock holder)
            If no active lock, pid will be -1.
        """
        lock_path = self.data_path("lock")
        no_lock = (-1, "")
        if not os.path.exists(lock_path):
            return no_lock
        lock_content = util.load_file(lock_path)
        [lock_pid, lock_holder] = lock_content.split(":")
        try:
            util.subp(["ps", lock_pid])
            return (int(lock_pid), lock_holder)
        except exceptions.ProcessExecutionError:
            if os.getuid() != 0:
                logging.debug(
                    "Found stale lock file previously held by %s:%s",
                    lock_pid,
                    lock_holder,
                )
                return (int(lock_pid), lock_holder)
            logging.warning(
                "Removing stale lock file previously held by %s:%s",
                lock_pid,
                lock_holder,
            )
            os.unlink(lock_path)
            return no_lock

    @property
    def data_dir(self):
        return self.cfg["data_dir"]

    @property
    def log_level(self):
        log_level = self.cfg.get("log_level")
        try:
            return getattr(logging, log_level.upper())
        except AttributeError:
            return getattr(logging, CONFIG_DEFAULTS["log_level"])

    def add_notice(self, label: str, description: str):
        """Add a notice message to notices cache.

        Such notices are seen in the Notices section from ua status output.
        They are also present in the JSON status output.
        """
        notices = self.read_cache("notices") or []
        notice = [label, description]
        if notice not in notices:
            notices.append(notice)
            self.write_cache("notices", notices)

    def remove_notice(self, label_regex: str, descr_regex: str):
        """Remove matching notices if present.

        :param label_regex: Regex used to remove notices with matching labels.
        :param descr_regex: Regex used to remove notices with matching
            descriptions.
        """
        notices = []
        cached_notices = self.read_cache("notices")
        if cached_notices:
            for notice_label, notice_descr in cached_notices:
                if re.match(label_regex, notice_label):
                    if re.match(descr_regex, notice_descr):
                        continue
                notices.append((notice_label, notice_descr))
        if notices:
            self.write_cache("notices", notices)
        elif os.path.exists(self.data_path("notices")):
            util.remove_file(self.data_path("notices"))

    @property
    def log_file(self) -> str:
        return self.cfg.get("log_file", CONFIG_DEFAULTS["log_file"])

    @property
    def timer_log_file(self) -> str:
        return self.cfg.get(
            "timer_log_file", CONFIG_DEFAULTS["timer_log_file"]
        )

    @property
    def daemon_log_file(self):
        return self.cfg.get(
            "daemon_log_file", CONFIG_DEFAULTS["daemon_log_file"]
        )

    @property
    def entitlements(self):
        """Return configured entitlements keyed by entitlement named"""
        if self._entitlements:
            return self._entitlements
        if not self.machine_token:
            return {}
        self._entitlements = self.get_entitlements_from_token(
            self.machine_token
        )
        return self._entitlements

    @staticmethod
    def get_entitlements_from_token(machine_token: Dict):
        """Return a dictionary of entitlements keyed by entitlement name.

        Return an empty dict if no entitlements are present.
        """
        if not machine_token:
            return {}

        entitlements = {}
        contractInfo = machine_token.get("machineTokenInfo", {}).get(
            "contractInfo"
        )
        if not contractInfo:
            return {}

        tokens_by_name = dict(
            (e.get("type"), e.get("token"))
            for e in machine_token.get("resourceTokens", [])
        )
        ent_by_name = dict(
            (e.get("type"), e)
            for e in contractInfo.get("resourceEntitlements", [])
        )
        for entitlement_name, ent_value in ent_by_name.items():
            entitlement_cfg = {"entitlement": ent_value}
            if entitlement_name in tokens_by_name:
                entitlement_cfg["resourceToken"] = tokens_by_name[
                    entitlement_name
                ]
            util.apply_contract_overrides(entitlement_cfg)
            entitlements[entitlement_name] = entitlement_cfg
        return entitlements

    @property
    def contract_expiry_datetime(self) -> datetime:
        """Return a datetime of the attached contract expiration."""
        if not self._contract_expiry_datetime:
            self._contract_expiry_datetime = self.machine_token[
                "machineTokenInfo"
            ]["contractInfo"]["effectiveTo"]

        return self._contract_expiry_datetime

    @property
    def is_attached(self):
        """Report whether this machine configuration is attached to UA."""
        return bool(self.machine_token)  # machine_token is removed on detach

    @property
    def contract_remaining_days(self) -> int:
        """Report num days until contract expiration based on effectiveTo

        :return: A positive int representing the number of days the attached
            contract remains in effect. Return a negative int for the number
            of days beyond contract's effectiveTo date.
        """
        delta = self.contract_expiry_datetime.date() - datetime.utcnow().date()
        return delta.days

    @property
    def features(self):
        """Return a dictionary of any features provided in uaclient.conf."""
        features = self.cfg.get("features")
        if features:
            if isinstance(features, dict):
                return features
            else:
                logging.warning(
                    "Unexpected uaclient.conf features value."
                    " Expected dict, but found %s",
                    features,
                )
        return {}

    @property
    def machine_token(self):
        """Return the machine-token if cached in the machine token response."""
        if not self._machine_token:
            raw_machine_token = self.read_cache("machine-token")

            machine_token_overlay_path = self.features.get(
                "machine_token_overlay"
            )

            if raw_machine_token and machine_token_overlay_path:
                machine_token_overlay = self.parse_machine_token_overlay(
                    machine_token_overlay_path
                )

                if machine_token_overlay:
                    depth_first_merge_overlay_dict(
                        base_dict=raw_machine_token,
                        overlay_dict=machine_token_overlay,
                    )

            self._machine_token = raw_machine_token

        return self._machine_token

    @property
    def activity_token(self) -> "Optional[str]":
        if self.machine_token:
            return self.machine_token.get("activityInfo", {}).get(
                "activityToken"
            )
        return None

    @property
    def activity_id(self) -> "Optional[str]":
        if self.machine_token:
            return self.machine_token.get("activityInfo", {}).get("activityID")
        return None

    @property
    def activity_ping_interval(self) -> "Optional[int]":
        if self.machine_token:
            return self.machine_token.get("activityInfo", {}).get(
                "activityPingInterval"
            )
        return None

    @property
    def contract_id(self):
        if self.machine_token:
            return (
                self.machine_token.get("machineTokenInfo", {})
                .get("contractInfo", {})
                .get("id")
            )
        return None

    def parse_machine_token_overlay(self, machine_token_overlay_path):
        if not os.path.exists(machine_token_overlay_path):
            raise exceptions.UserFacingError(
                messages.INVALID_PATH_FOR_MACHINE_TOKEN_OVERLAY.format(
                    file_path=machine_token_overlay_path
                )
            )

        try:
            machine_token_overlay_content = util.load_file(
                machine_token_overlay_path
            )

            return json.loads(machine_token_overlay_content)
        except ValueError as e:
            raise exceptions.UserFacingError(
                messages.ERROR_JSON_DECODING_IN_FILE.format(
                    error=str(e), file_path=machine_token_overlay_path
                )
            )

    def data_path(self, key: Optional[str] = None) -> str:
        """Return the file path in the data directory represented by the key"""
        data_dir = self.cfg["data_dir"]
        if not key:
            return os.path.join(data_dir, PRIVATE_SUBDIR)
        if key in self.data_paths:
            data_path = self.data_paths[key]
            if data_path.private:
                return os.path.join(
                    data_dir, PRIVATE_SUBDIR, data_path.filename
                )
            return os.path.join(data_dir, data_path.filename)
        return os.path.join(data_dir, PRIVATE_SUBDIR, key)

    def cache_key_exists(self, key: str) -> bool:
        cache_path = self.data_path(key)
        return os.path.exists(cache_path)

    def _perform_delete(self, cache_path: str) -> None:
        """Delete the given cache_path if it exists.

        (This is a separate method to allow easier disabling of deletion during
        tests.)
        """
        if os.path.exists(cache_path):
            os.unlink(cache_path)

    def delete_cache_key(self, key: str) -> None:
        """Remove specific cache file."""
        if not key:
            raise RuntimeError(
                "Invalid or empty key provided to delete_cache_key"
            )
        if key.startswith("machine-access") or key == "machine-token":
            self._entitlements = None
            self._machine_token = None
        elif key == "lock":
            self.remove_notice("", "Operation in progress.*")
        cache_path = self.data_path(key)
        self._perform_delete(cache_path)

    def delete_cache(self, delete_permanent: bool = False):
        """
        Remove configuration cached response files class attributes.

        :param delete_permanent: even delete the "permanent" files
        """
        for path_key in self.data_paths.keys():
            if delete_permanent or not self.data_paths[path_key].permanent:
                self.delete_cache_key(path_key)

    def read_cache(self, key: str, silent: bool = False) -> Optional[Any]:
        cache_path = self.data_path(key)
        try:
            content = util.load_file(cache_path)
        except Exception:
            if not os.path.exists(cache_path) and not silent:
                logging.debug("File does not exist: %s", cache_path)
            return None
        try:
            return json.loads(content, cls=util.DatetimeAwareJSONDecoder)
        except ValueError:
            return content

    def write_cache(self, key: str, content: Any) -> None:
        filepath = self.data_path(key)
        data_dir = os.path.dirname(filepath)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            if os.path.basename(data_dir) == PRIVATE_SUBDIR:
                os.chmod(data_dir, 0o700)
        if key.startswith("machine-access") or key == "machine-token":
            self._machine_token = None
            self._entitlements = None
        elif key == "lock":
            if ":" in content:
                self.add_notice(
                    "",
                    "Operation in progress: {}".format(content.split(":")[1]),
                )
        if not isinstance(content, str):
            content = json.dumps(content, cls=util.DatetimeAwareJSONEncoder)
        mode = 0o600
        if key in self.data_paths:
            if not self.data_paths[key].private:
                mode = 0o644
        util.write_file(filepath, content, mode=mode)

    def process_config(self):
        for prop in (
            "update_messaging_timer",
            "update_status_timer",
            "metering_timer",
        ):
            value = getattr(self, prop)
            if value is None:
                logging.debug(
                    "No config set for {}, default value will be used."
                )
            elif not isinstance(value, int) or value < 0:
                error_msg = (
                    "Value for the {} interval must be a positive integer. "
                    "Default value will be used."
                ).format(prop)
                raise exceptions.UserFacingError(error_msg)

        if (self.global_apt_http_proxy or self.global_apt_https_proxy) and (
            self.ua_apt_http_proxy or self.ua_apt_https_proxy
        ):
            # Should we unset the config values?
            raise exceptions.UserFacingError(
                messages.ERROR_PROXY_CONFIGURATION
            )

        util.validate_proxy(
            "http",
            self.global_apt_http_proxy,
            util.PROXY_VALIDATION_APT_HTTP_URL,
        )
        util.validate_proxy(
            "https",
            self.global_apt_https_proxy,
            util.PROXY_VALIDATION_APT_HTTPS_URL,
        )
        util.validate_proxy(
            "http", self.ua_apt_http_proxy, util.PROXY_VALIDATION_APT_HTTP_URL
        )
        util.validate_proxy(
            "https",
            self.ua_apt_https_proxy,
            util.PROXY_VALIDATION_APT_HTTPS_URL,
        )
        util.validate_proxy(
            "http", self.http_proxy, util.PROXY_VALIDATION_SNAP_HTTP_URL
        )
        util.validate_proxy(
            "https", self.https_proxy, util.PROXY_VALIDATION_SNAP_HTTPS_URL
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
        if snap.is_installed():
            snap.configure_snap_proxy(self.http_proxy, self.https_proxy)
            if (
                not self.http_proxy
                and snap.get_config_option_value(snap.HTTP_PROXY_OPTION)
            ) or (
                not self.https_proxy
                and snap.get_config_option_value(snap.HTTPS_PROXY_OPTION)
            ):
                services_with_proxies.append("snap")

        from uaclient.entitlements import livepatch
        from uaclient.entitlements.entitlement_status import ApplicationStatus

        livepatch_ent = livepatch.LivepatchEntitlement()
        livepatch_status, _ = livepatch_ent.application_status()

        if livepatch_status == ApplicationStatus.ENABLED:
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

    def write_cfg(self, config_path=None):
        """Write config values back to config_path or DEFAULT_CONFIG_FILE."""
        if not config_path:
            config_path = DEFAULT_CONFIG_FILE
        content = messages.UACLIENT_CONF_HEADER
        cfg_dict = copy.deepcopy(self.cfg)
        if "log_level" not in cfg_dict:
            cfg_dict["log_level"] = CONFIG_DEFAULTS["log_level"]
        # Ensure defaults are present in uaclient.conf if absent
        for attr in (
            "contract_url",
            "security_url",
            "data_dir",
            "log_file",
            "timer_log_file",
            "daemon_log_file",
        ):
            cfg_dict[attr] = getattr(self, attr)

        # Each UA_CONFIGURABLE_KEY needs to have a property on UAConfig
        # which reads the proper key value or returns a default
        cfg_dict["ua_config"] = {
            key: getattr(self, key, None) for key in UA_CONFIGURABLE_KEYS
        }

        content += yaml.dump(cfg_dict, default_flow_style=False)
        util.write_file(config_path, content)

    def warn_about_invalid_keys(self):
        if self.invalid_keys is not None:
            for invalid_key in sorted(self.invalid_keys):
                logging.warning(
                    "Ignoring invalid uaclient.conf key: %s", invalid_key
                )


def get_config_path() -> str:
    """Get config path to be used when loading config dict."""
    config_file = os.environ.get("UA_CONFIG_FILE")
    if config_file:
        return config_file

    local_cfg = os.path.join(
        os.getcwd(), os.path.basename(DEFAULT_CONFIG_FILE)
    )
    if os.path.exists(local_cfg):
        return local_cfg

    return DEFAULT_CONFIG_FILE


def parse_config(config_path=None):
    """Parse known UA config file

    Attempt to find configuration in cwd and fallback to DEFAULT_CONFIG_FILE.
    Any missing configuration keys will be set to CONFIG_DEFAULTS.

    Values are overridden by any environment variable with prefix 'UA_'.

    @param config_path: Fullpath to ua configfile. If unspecified, use
        DEFAULT_CONFIG_FILE.

    @return: Dict of configuration values.
    """
    cfg = copy.copy(CONFIG_DEFAULTS)

    if not config_path:
        config_path = get_config_path()

    LOG.debug("Using UA client configuration file at %s", config_path)
    if os.path.exists(config_path):
        cfg.update(yaml.safe_load(util.load_file(config_path)))
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
                        value = yaml.safe_load(util.load_file(value))
                    else:
                        raise exceptions.UserFacingError(
                            "Could not find yaml file: {}".format(value)
                        )

                if "features" not in cfg:
                    cfg["features"] = {feature_field_name: value}
                else:
                    cfg["features"][feature_field_name] = value
            elif key in CONFIG_FIELD_ENVVAR_ALLOWLIST:
                env_keys[field_name] = value
    cfg.update(env_keys)
    cfg["data_dir"] = os.path.expanduser(cfg["data_dir"])
    for key in ("contract_url", "security_url"):
        if not util.is_service_url(cfg[key]):
            raise exceptions.UserFacingError(
                "Invalid url in config. {}: {}".format(key, cfg[key])
            )

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


def depth_first_merge_overlay_dict(base_dict, overlay_dict):
    """Merge the contents of overlay dict into base_dict not only on top-level
    keys, but on all on the depths of the overlay_dict object. For example,
    using these values as entries for the function:

    base_dict = {"a": 1, "b": {"c": 2, "d": 3}}
    overlay_dict = {"b": {"c": 10}}

    Should update base_dict into:

    {"a": 1, "b": {"c": 10, "d": 3}}

    @param base_dict: The dict to be updated
    @param overlay_dict: The dict with information to be added into base_dict
    """

    def update_dict_list(base_values, overlay_values, key):
        values_to_append = []
        id_key = MERGE_ID_KEY_MAP.get(key)
        for overlay_value in overlay_values:
            was_replaced = False
            for base_value_idx, base_value in enumerate(base_values):
                if base_value.get(id_key) == overlay_value.get(id_key):
                    depth_first_merge_overlay_dict(base_value, overlay_value)
                    was_replaced = True

            if not was_replaced:
                values_to_append.append(overlay_value)

        base_values.extend(values_to_append)

    for key, value in overlay_dict.items():
        base_value = base_dict.get(key)
        if isinstance(base_value, dict) and isinstance(value, dict):
            depth_first_merge_overlay_dict(base_dict[key], value)
        elif isinstance(base_value, list) and isinstance(value, list):
            if len(base_value) and isinstance(base_value[0], dict):
                update_dict_list(base_dict[key], value, key=key)
            else:
                """
                Most other lists which aren't lists of dicts are lists of
                strs. Replace that list # with the overlay value."""
                base_dict[key] = value
        else:
            base_dict[key] = value
