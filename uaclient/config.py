import copy
from datetime import datetime
from functools import wraps
import json
import logging
import os
import re
import sys
import yaml
from collections import namedtuple, OrderedDict

from uaclient import apt, exceptions, snap, status, util, version
from uaclient.defaults import (
    CONFIG_DEFAULTS,
    CONFIG_FIELD_ENVVAR_ALLOWLIST,
    DEFAULT_CONFIG_FILE,
    BASE_CONTRACT_URL,
    BASE_SECURITY_URL,
)

try:
    from typing import (  # noqa: F401
        Any,
        cast,
        Dict,
        List,
        Optional,
        Tuple,
        Union,
    )
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    def cast(_, x):  # type: ignore
        return x


DEFAULT_STATUS = {
    "_doc": "Content provided in json response is currently considered"
    " Experimental and may change",
    "_schema_version": "0.1",
    "version": version.get_version(),
    "machine_id": None,
    "attached": False,
    "effective": None,
    "expires": None,  # TODO Will this break something?
    "origin": None,
    "services": [],
    "execution_status": status.UserFacingConfigStatus.INACTIVE.value,
    "execution_details": status.MESSAGE_NO_ACTIVE_OPERATIONS,
    "notices": [],
    "contract": {
        "id": "",
        "name": "",
        "created_at": "",
        "products": [],
        "tech_support_level": status.UserFacingStatus.INAPPLICABLE.value,
    },
    "account": {
        "name": "",
        "id": "",
        "created_at": "",
        "external_account_ids": [],
    },
}  # type: Dict[str, Any]

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
)


# A data path is a filename, and an attribute ("private") indicating whether it
# should only be readable by root
DataPath = namedtuple("DataPath", ("filename", "private"))


class UAConfig:

    data_paths = {
        "instance-id": DataPath("instance-id", True),
        "machine-access-cis": DataPath("machine-access-cis.json", True),
        "machine-id": DataPath("machine-id", True),
        "machine-token": DataPath("machine-token.json", True),
        "lock": DataPath("lock", True),
        "status-cache": DataPath("status.json", False),
        "notices": DataPath("notices.json", False),
        "marker-reboot-cmds": DataPath("marker-reboot-cmds-required", False),
        "services-once-enabled": DataPath("services-once-enabled", False),
    }  # type: Dict[str, DataPath]

    _entitlements = None  # caching to avoid repetitive file reads
    _machine_token = None  # caching to avoid repetitive file reading
    _contract_expiry_datetime = None

    def __init__(
        self, cfg: "Dict[str, Any]" = None, series: str = None
    ) -> None:
        """"""
        if cfg:
            self.cfg_path = None
            self.cfg = cfg
        else:
            self.cfg_path = get_config_path()
            self.cfg = parse_config(self.cfg_path)

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
    def http_proxy(self) -> "Optional[str]":
        return self.cfg.get("ua_config", {}).get("http_proxy")

    @http_proxy.setter
    def http_proxy(self, value: str):
        if "ua_config" not in self.cfg:
            self.cfg["ua_config"] = {}
        self.cfg["ua_config"]["http_proxy"] = value
        self.write_cfg()

    @property
    def https_proxy(self) -> "Optional[str]":
        return self.cfg.get("ua_config", {}).get("https_proxy")

    @https_proxy.setter
    def https_proxy(self, value: str):
        if "ua_config" not in self.cfg:
            self.cfg["ua_config"] = {}
        self.cfg["ua_config"]["https_proxy"] = value
        self.write_cfg()

    @property
    def apt_http_proxy(self) -> "Optional[str]":
        return self.cfg.get("ua_config", {}).get("apt_http_proxy")

    @apt_http_proxy.setter
    def apt_http_proxy(self, value: str):
        if "ua_config" not in self.cfg:
            self.cfg["ua_config"] = {}
        self.cfg["ua_config"]["apt_http_proxy"] = value
        self.write_cfg()

    @property
    def apt_https_proxy(self) -> "Optional[str]":
        return self.cfg.get("ua_config", {}).get("apt_https_proxy")

    @apt_https_proxy.setter
    def apt_https_proxy(self, value: str):
        if "ua_config" not in self.cfg:
            self.cfg["ua_config"] = {}
        self.cfg["ua_config"]["apt_https_proxy"] = value
        self.write_cfg()

    def check_lock_info(self) -> "Tuple[int, str]":
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
        except util.ProcessExecutionError:
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
    def log_file(self):
        return self.cfg.get("log_file", CONFIG_DEFAULTS["log_file"])

    @property
    def entitlements(self):
        """Return a dictionary of entitlements keyed by entitlement name.

        Return an empty dict if no entitlements are present.
        """
        if self._entitlements:
            return self._entitlements
        machine_token = self.machine_token
        if not machine_token:
            return {}

        self._entitlements = {}
        contractInfo = machine_token["machineTokenInfo"]["contractInfo"]
        tokens_by_name = dict(
            (e["type"], e["token"])
            for e in machine_token.get("resourceTokens", [])
        )
        ent_by_name = dict(
            (e["type"], e) for e in contractInfo["resourceEntitlements"]
        )
        for entitlement_name, ent_value in ent_by_name.items():
            entitlement_cfg = {"entitlement": ent_value}
            if entitlement_name in tokens_by_name:
                entitlement_cfg["resourceToken"] = tokens_by_name[
                    entitlement_name
                ]
            util.apply_series_overrides(entitlement_cfg, self.series)
            self._entitlements[entitlement_name] = entitlement_cfg
        return self._entitlements

    @property
    def contract_expiry_datetime(self) -> "datetime":
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

    def parse_machine_token_overlay(self, machine_token_overlay_path):
        if not os.path.exists(machine_token_overlay_path):
            raise exceptions.UserFacingError(
                status.INVALID_PATH_FOR_MACHINE_TOKEN_OVERLAY.format(
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
                status.ERROR_JSON_DECODING_IN_FILE.format(
                    error=str(e), file_path=machine_token_overlay_path
                )
            )

    def data_path(self, key: "Optional[str]" = None) -> str:
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

    def delete_cache(self):
        """Remove configuration cached response files class attributes."""
        for path_key in self.data_paths.keys():
            self.delete_cache_key(path_key)

    def read_cache(self, key: str, silent: bool = False) -> "Optional[Any]":
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

    def write_cache(self, key: str, content: "Any") -> None:
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

    def _remove_beta_resources(self, response) -> "Dict[str, Any]":
        """ Remove beta services from response dict"""
        from uaclient.entitlements import ENTITLEMENT_CLASS_BY_NAME

        new_response = copy.deepcopy(response)

        released_resources = []
        for resource in new_response.get("services", {}):
            resource_name = resource["name"]
            ent_cls = ENTITLEMENT_CLASS_BY_NAME.get(resource_name)

            if ent_cls is None:
                """
                Here we cannot know the status of a service,
                since it is not listed as a valid entitlement.
                Therefore, we keep this service in the list, since
                we cannot validate if it is a beta service or not.
                """
                released_resources.append(resource)
                continue

            enabled_status = status.UserFacingStatus.ACTIVE.value
            if (
                not ent_cls.is_beta
                or resource.get("status", "") == enabled_status
            ):
                released_resources.append(resource)

        if released_resources:
            new_response["services"] = released_resources

        return new_response

    def _get_config_status(self) -> "Dict[str, Any]":
        """Return a dict with execution_status, execution_details and notices.

            Values for execution_status will be one of UserFacingConfigStatus
            enum:
                inactive, active, reboot-required
            execution_details will provide more details about that state.
            notices is a list of tuples with label and description items.
        """
        userStatus = status.UserFacingConfigStatus
        status_val = userStatus.INACTIVE.value
        status_desc = status.MESSAGE_NO_ACTIVE_OPERATIONS
        (lock_pid, lock_holder) = self.check_lock_info()
        notices = self.read_cache("notices") or []
        if lock_pid > 0:
            status_val = userStatus.ACTIVE.value
            status_desc = status.MESSAGE_LOCK_HELD.format(
                pid=lock_pid, lock_holder=lock_holder
            )
        elif os.path.exists(self.data_path("marker-reboot-cmds")):
            status_val = userStatus.REBOOTREQUIRED.value
            operation = "configuration changes"
            for label, description in notices:
                if label == "Reboot required":
                    operation = description
                    break
            status_desc = status.MESSAGE_ENABLE_REBOOT_REQUIRED_TMPL.format(
                operation=operation
            )
        return {
            "execution_status": status_val,
            "execution_details": status_desc,
            "notices": notices,
            "config_path": self.cfg_path,
            "config": self.cfg,
        }

    def _unattached_status(self) -> "Dict[str, Any]":
        """Return unattached status as a dict."""
        from uaclient.contract import get_available_resources
        from uaclient.entitlements import ENTITLEMENT_CLASS_BY_NAME

        response = copy.deepcopy(DEFAULT_STATUS)
        response["version"] = version.get_version(features=self.features)

        resources = get_available_resources(self)
        for resource in sorted(resources, key=lambda x: x["name"]):
            if resource["available"]:
                available = status.UserFacingAvailability.AVAILABLE.value
            else:
                available = status.UserFacingAvailability.UNAVAILABLE.value
            ent_cls = ENTITLEMENT_CLASS_BY_NAME.get(resource["name"])

            if not ent_cls:
                LOG.debug(
                    "Ignoring availability of unknown service %s"
                    " from contract server",
                    resource["name"],
                )
                continue

            response["services"].append(
                {
                    "name": resource["name"],
                    "description": ent_cls.description,
                    "available": available,
                }
            )
        return response

    def _attached_service_status(
        self, ent, inapplicable_resources
    ) -> "Dict[str, Optional[str]]":
        details = ""
        description_override = None
        contract_status = ent.contract_status()
        if contract_status == status.ContractStatus.UNENTITLED:
            ent_status = status.UserFacingStatus.UNAVAILABLE
        else:
            if ent.name in inapplicable_resources:
                ent_status = status.UserFacingStatus.INAPPLICABLE
                description_override = inapplicable_resources[ent.name]
            else:
                ent_status, details = ent.user_facing_status()

        return {
            "name": ent.name,
            "description": ent.description,
            "entitled": contract_status.value,
            "status": ent_status.value,
            "status_details": details,
            "description_override": description_override,
            "available": "yes"
            if ent.name not in inapplicable_resources
            else "no",
        }

    def _attached_status(self) -> "Dict[str, Any]":
        """Return configuration of attached status as a dictionary."""
        from uaclient.contract import get_available_resources
        from uaclient.entitlements import ENTITLEMENT_CLASSES

        response = copy.deepcopy(DEFAULT_STATUS)
        machineTokenInfo = self.machine_token["machineTokenInfo"]
        contractInfo = machineTokenInfo["contractInfo"]
        tech_support_level = status.UserFacingStatus.INAPPLICABLE.value
        response.update(
            {
                "version": version.get_version(features=self.features),
                "machine_id": machineTokenInfo["machineId"],
                "attached": True,
                "origin": contractInfo.get("origin"),
                "notices": self.read_cache("notices") or [],
                "contract": {
                    "id": contractInfo["id"],
                    "name": contractInfo["name"],
                    "created_at": contractInfo.get("createdAt", ""),
                    "products": contractInfo.get("products", []),
                    "tech_support_level": tech_support_level,
                },
                "account": {
                    "name": self.accounts[0]["name"],
                    "id": self.accounts[0]["id"],
                    "created_at": self.accounts[0].get("createdAt", ""),
                    "external_account_ids": self.accounts[0].get(
                        "externalAccountIDs", []
                    ),
                },
            }
        )
        if contractInfo.get("effectiveTo"):
            response["expires"] = self.contract_expiry_datetime
        if contractInfo.get("effectiveFrom"):
            response["effective"] = contractInfo["effectiveFrom"]

        resources = self.machine_token.get("availableResources")
        if not resources:
            resources = get_available_resources(self)

        inapplicable_resources = {
            resource["name"]: resource.get("description")
            for resource in sorted(resources, key=lambda x: x["name"])
            if not resource["available"]
        }

        for ent_cls in ENTITLEMENT_CLASSES:
            ent = ent_cls(self)
            response["services"].append(
                self._attached_service_status(ent, inapplicable_resources)
            )

        support = self.entitlements.get("support", {}).get("entitlement")
        if support:
            supportLevel = support.get("affordances", {}).get("supportLevel")
            if supportLevel:
                response["contract"]["tech_support_level"] = supportLevel
        return response

    def status(self, show_beta=False) -> "Dict[str, Any]":
        """Return status as a dict, using a cache for non-root users

        When unattached, get available resources from the contract service
        to report detailed availability of different resources for this
        machine.

        Write the status-cache when called by root.
        """

        if os.getuid() != 0:
            response = cast("Dict[str, Any]", self.read_cache("status-cache"))
            if not response:
                response = self._unattached_status()
        elif not self.is_attached:
            response = self._unattached_status()
        else:
            response = self._attached_status()
        response.update(self._get_config_status())
        if os.getuid() == 0:
            self.write_cache("status-cache", response)

            # Try to remove fix reboot notices if not applicable
            if not util.should_reboot():
                self.remove_notice(
                    "",
                    status.MESSAGE_ENABLE_REBOOT_REQUIRED_TMPL.format(
                        operation="fix operation"
                    ),
                )

        config_allow_beta = util.is_config_value_true(
            config=self.cfg, path_to_value="features.allow_beta"
        )
        show_beta |= config_allow_beta
        if not show_beta:
            response = self._remove_beta_resources(response)

        return response

    def help(self, name):
        """Return help information from an uaclient service as a dict

        :param name: Name of the service for which to return help data.

        :raises: UserFacingError when no help is available.
        """
        from uaclient.contract import get_available_resources
        from uaclient.entitlements import ENTITLEMENT_CLASS_BY_NAME

        resources = get_available_resources(self)
        help_resource = None

        # We are using an OrderedDict here to guarantee
        # that if we need to print the result of this
        # dict, the order of insertion will always be respected
        response_dict = OrderedDict()
        response_dict["name"] = name

        for resource in resources:
            if resource["name"] == name and name in ENTITLEMENT_CLASS_BY_NAME:
                help_resource = resource
                help_ent_cls = ENTITLEMENT_CLASS_BY_NAME.get(name)
                help_ent = help_ent_cls(self)
                break

        if help_resource is None:
            raise exceptions.UserFacingError(
                "No help available for '{}'".format(name)
            )

        if self.is_attached:
            service_status = self._attached_service_status(help_ent, {})
            status_msg = service_status["status"]

            response_dict["entitled"] = service_status["entitled"]
            response_dict["status"] = status_msg

            if status_msg == "enabled" and help_ent_cls.is_beta:
                response_dict["beta"] = True

        else:
            if help_resource["available"]:
                available = status.UserFacingAvailability.AVAILABLE.value
            else:
                available = status.UserFacingAvailability.UNAVAILABLE.value

            response_dict["available"] = available

        response_dict["help"] = help_ent.help_info
        return response_dict

    def process_config(self):
        util.validate_proxy(
            "http", self.apt_http_proxy, util.PROXY_VALIDATION_APT_HTTP_URL
        )
        util.validate_proxy(
            "https", self.apt_https_proxy, util.PROXY_VALIDATION_APT_HTTPS_URL
        )
        util.validate_proxy(
            "http", self.http_proxy, util.PROXY_VALIDATION_SNAP_HTTP_URL
        )
        util.validate_proxy(
            "https", self.https_proxy, util.PROXY_VALIDATION_SNAP_HTTPS_URL
        )

        apt.setup_apt_proxy(self.apt_http_proxy, self.apt_https_proxy)

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

        livepatch_ent = livepatch.LivepatchEntitlement()
        livepatch_status, _ = livepatch_ent.application_status()

        if livepatch_status == status.ApplicationStatus.ENABLED:
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
                status.MESSAGE_PROXY_DETECTED_BUT_NOT_CONFIGURED.format(
                    services=services
                )
            )

    def write_cfg(self, config_path=None):
        """Write config values back to config_path or DEFAULT_CONFIG_FILE."""
        if not config_path:
            config_path = DEFAULT_CONFIG_FILE
        content = status.MESSAGE_UACLIENT_CONF_HEADER
        cfg_dict = copy.deepcopy(self.cfg)
        if "log_level" not in cfg_dict:
            cfg_dict["log_level"] = CONFIG_DEFAULTS["log_level"]
        # Ensure defaults are present in uaclient.conf if absent
        for attr in ("contract_url", "security_url", "data_dir", "log_file"):
            cfg_dict[attr] = getattr(self, attr)

        # Each UA_CONFIGURABLE_KEY needs to have a property on UAConfig
        # which reads the proper key value or returns a default
        cfg_dict["ua_config"] = {
            key: getattr(self, key) for key in UA_CONFIGURABLE_KEYS
        }

        content += yaml.dump(cfg_dict, default_flow_style=False)
        util.write_file(config_path, content)


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
    # log about invalid keys before ignoring
    for key in sorted(set(cfg.keys()).difference(VALID_UA_CONFIG_KEYS)):
        logging.warning(
            "Ignoring invalid uaclient.conf key: %s=%s", key, cfg.pop(key)
        )

    return cfg


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
            cfg = parse_config()
            value_override = cfg.get("settings_overrides", {}).get(
                override_key, UNSET_SETTINGS_OVERRIDE_KEY
            )

            if value_override != UNSET_SETTINGS_OVERRIDE_KEY:
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


def update_ua_messages(cfg: UAConfig):
    """Helper to load and run ua_update_messaging.

    This is needed because we don't have /usr/lib/ubuntu-advantage
    python scripts in our path and we don't want to shell out with
    subp to call python3 /path/to/ua_update_messaging.py.
    """
    sys.path.append("/usr/lib/ubuntu-advantage")
    try:
        __import__("ua_update_messaging")
        update_msgs = getattr(
            sys.modules["ua_update_messaging"], "update_apt_and_motd_messages"
        )
        update_msgs(cfg)
    except ImportError:
        logging.debug(
            "Unable to update UA messages. Cannot import ua_update_messaging."
        )
    finally:
        sys.path.pop()
