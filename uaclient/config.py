import copy
from datetime import datetime
import json
import logging
import os
import yaml
from collections import namedtuple

from uaclient import status, util
from uaclient.defaults import CONFIG_DEFAULTS, DEFAULT_CONFIG_FILE
from uaclient import exceptions

try:
    from typing import Any, cast, Dict, Optional  # noqa: F401
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    def cast(_, x):  # type: ignore
        return x


DEFAULT_STATUS = {
    "_doc": "Content provided in json response is currently considered"
    " Experimental and may change",
    "attached": False,
    "expires": status.UserFacingStatus.INAPPLICABLE.value,
    "origin": None,
    "services": [],
    "techSupportLevel": status.UserFacingStatus.INAPPLICABLE.value,
}  # type: Dict[str, Any]

LOG = logging.getLogger(__name__)

PRIVATE_SUBDIR = "private"


# A data path is a filename, and an attribute ("private") indicating whether it
# should only be readable by root
DataPath = namedtuple("DataPath", ("filename", "private"))


class UAConfig:

    data_paths = {
        "instance-id": DataPath("instance-id", True),
        "machine-id": DataPath("machine-id", True),
        "machine-token": DataPath("machine-token.json", True),
        "status-cache": DataPath("status.json", False),
    }  # type: Dict[str, DataPath]

    _entitlements = None  # caching to avoid repetitive file reads
    _machine_token = None  # caching to avoid repetitive file reading

    def __init__(self, cfg: "Dict[str, Any]" = None) -> None:
        """"""
        if cfg:
            self.cfg = cfg
        else:
            self.cfg = parse_config()

    @property
    def accounts(self):
        """Return the list of accounts that apply to this authorized user."""
        if self.is_attached:
            accountInfo = self.machine_token["machineTokenInfo"]["accountInfo"]
            return [accountInfo]
        return []

    @property
    def contract_url(self):
        return self.cfg.get("contract_url", "https://contracts.canonical.com")

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
            util.apply_series_overrides(entitlement_cfg)
            self._entitlements[entitlement_name] = entitlement_cfg
        return self._entitlements

    @property
    def is_attached(self):
        """Report whether this machine configuration is attached to UA."""
        return bool(self.machine_token)  # machine_token is removed on detach

    @property
    def machine_token(self):
        """Return the machine-token if cached in the machine token response."""
        if not self._machine_token:
            self._machine_token = self.read_cache("machine-token")
        return self._machine_token

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
        if key == "machine-token":
            self._entitlements = None
            self._machine_token = None
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
        if key == "machine-token":
            self._machine_token = None
            self._entitlements = None
        if not isinstance(content, str):
            content = json.dumps(content, cls=util.DatetimeAwareJSONEncoder)
        mode = 0o600
        if key in self.data_paths:
            if not self.data_paths[key].private:
                mode = 0o644
        util.write_file(filepath, content, mode=mode)

    def _unattached_status(self) -> "Dict[str, Any]":
        """Return unattached status as a dict."""
        from uaclient.contract import get_available_resources
        from uaclient.entitlements import ENTITLEMENT_CLASS_BY_NAME

        response = copy.deepcopy(DEFAULT_STATUS)
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
            "statusDetails": details,
            "description_override": description_override,
        }

    def _attached_status(self) -> "Dict[str, Any]":
        """Return configuration of attached status as a dictionary."""
        from uaclient.contract import get_available_resources
        from uaclient.entitlements import ENTITLEMENT_CLASSES

        response = copy.deepcopy(DEFAULT_STATUS)
        contractInfo = self.machine_token["machineTokenInfo"]["contractInfo"]
        response.update(
            {
                "attached": True,
                "account": self.accounts[0]["name"],
                "account-id": self.accounts[0]["id"],
                "origin": contractInfo.get("origin"),
                "subscription": contractInfo["name"],
                "subscription-id": contractInfo["id"],
            }
        )
        if contractInfo.get("effectiveTo"):
            response["expires"] = datetime.strptime(
                contractInfo["effectiveTo"], "%Y-%m-%dT%H:%M:%SZ"
            )

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
            if not supportLevel:
                supportLevel = DEFAULT_STATUS["techSupportLevel"]
            response["techSupportLevel"] = supportLevel
        return response

    def status(self) -> "Dict[str, Any]":
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
        if os.getuid() == 0:
            self.write_cache("status-cache", response)
        return response


def parse_config(config_path=None):
    """Parse known UA config file

    Attempt to find configuration in cwd and fallback to DEFAULT_CONFIG_FILE.
    Any missing configuration keys will be set to CONFIG_DEFAULTS.

    Values are overridden by any environment variable with prefix 'UA_'.

    @param config_path: Fullpath to ua configfile. If unspecified, use
        DEFAULT_CONFIG_FILE.

    @return: Dict of configuration values.
    """
    if not config_path:
        config_path = DEFAULT_CONFIG_FILE
    cfg = copy.copy(CONFIG_DEFAULTS)
    local_cfg = os.path.join(os.getcwd(), os.path.basename(config_path))
    if os.path.exists(local_cfg):
        config_path = local_cfg
    if os.environ.get("UA_CONFIG_FILE"):
        config_path = os.environ.get("UA_CONFIG_FILE")
    LOG.debug("Using UA client configuration file at %s", config_path)
    if os.path.exists(config_path):
        cfg.update(yaml.safe_load(util.load_file(config_path)))
    env_keys = {}
    for key, value in os.environ.items():
        key = key.lower()
        if key.startswith("ua_"):
            env_keys[key[3:]] = value  # Strip leading UA_
    cfg.update(env_keys)
    cfg["log_level"] = cfg["log_level"].upper()
    cfg["data_dir"] = os.path.expanduser(cfg["data_dir"])
    if not util.is_service_url(cfg["contract_url"]):
        raise exceptions.UserFacingError(
            "Invalid url in config. contract_url: {}".format(
                cfg["contract_url"]
            )
        )
    return cfg
