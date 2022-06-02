import json
import logging
import os
from datetime import datetime
from typing import Dict, Optional

from uaclient import defaults, event_logger, schemas, util

PRIVATE_SUBDIR = "private"

event = event_logger.get_event_logger()
LOG = logging.getLogger(__name__)


class UAFile:
    _root_directory = defaults.DEFAULT_DATA_DIR
    _file_name = "file"

    def __init__(
        self,
        root_directory: Optional[str] = None,
        filename: Optional[str] = None,
        private: bool = True,
    ):
        if root_directory:
            self._root_directory = root_directory
        if filename:
            self._file_name = filename
        self._is_private = private
        self._filepath = None

    @property
    def filepath(self):
        if not self._filepath:
            self._filepath = os.path.join(
                self._root_directory, self._file_name
            )
        return self._filepath

    @property
    def is_private_file(self):
        return self._is_private

    def write(self, content):
        file_mode = 0o600 if self._is_private else 0o644
        self.create_file()
        if not isinstance(content, str):
            content = json.dumps(content, cls=util.DatetimeAwareJSONEncoder)
        util.write_file(self.filepath, content, file_mode)

    def read(self):
        content = None
        try:
            content = util.load_file(self.filepath)
        except FileNotFoundError:
            if not os.path.exists(self.filepath):
                LOG.debug("File does not exist: {}".format(self.filepath))
        return content

    def delete(self):
        util.remove_file(self.filepath)

    def create_file(self):
        file_dir = os.path.dirname(self.filepath)
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
            if self._is_private:
                os.chmod(file_dir, 0o700)


class PublicMachineTokenFile(UAFile):
    _file_name = defaults.PUBLIC_MACHINE_TOKEN_FILE
    _is_private = False

    def __init__(
        self,
        root_directory: Optional[str] = None,
    ):
        if root_directory:
            self._root_directory = root_directory
        file_name = defaults.PUBLIC_MACHINE_TOKEN_FILE
        is_private = False
        super().__init__(self._root_directory, file_name, is_private)

    def write(self, content):
        """
        Writes to the public file of the machine token
        It checks for new keys and filter the data
        """
        try:
            if isinstance(content, str):
                content = json.loads(content)
        except Exception:
            return None
        self.filter_tokens(schemas.contract_schema, content)
        content = json.dumps(content, cls=util.DatetimeAwareJSONEncoder)
        content = content.replace('"', "'")
        content = util.redact_sensitive_logs(content)
        content = content.replace("'", '"')
        super().write(content)

    def filter_tokens(self, schema, data):
        keys_to_del = []
        for k, v in data.items():
            if k not in schema:
                keys_to_del.append(k)
                LOG.debug(
                    "{key} not present in {schema}".format(
                        key=k, schema=schema
                    )
                )
            else:
                if isinstance(v, dict):
                    self.filter_tokens(schema[k], v)
                elif isinstance(v, list):
                    for i_v in v:
                        if isinstance(i_v, dict):
                            self.filter_tokens(schema[k][0], i_v)
        for k in keys_to_del:
            LOG.debug("Deleting {k} key from the data".format(k=k))
            if isinstance(data, Dict):
                del data[k]
            else:
                if k in data:
                    data.remove(k)


class MachineTokenFile:
    _machine_token = None
    _entitlements = None
    _contract_expiry_datetime = None

    def __init__(
        self, root_directory: Optional[str] = None, root_mode: bool = True
    ):
        self._rd = None
        self._fn = None
        if root_mode:  # private file
            if not root_directory:
                root_directory = defaults.DEFAULT_DATA_DIR + "/private"
            file_name = defaults.PRIVATE_MACHINE_TOKEN_FILE
            self._rd = root_directory
            self._fn = file_name
            self.file_handler = UAFile(root_directory, self._fn)
        else:  # public file
            self.file_handler = PublicMachineTokenFile(root_directory)

    def write(self, content):
        """Update the machine_token file for both pub/priv files"""
        self.file_handler.write(content)
        if self.file_handler.is_private_file:  # write to public file as well
            pub_file = PublicMachineTokenFile(self._rd)
            pub_file.write(content)
        self._machine_token = None
        self._entitlements = None

    def delete(self):
        """Delete both pub and priv files"""
        self.file_handler.delete()
        # Delete the other file as well
        if self.file_handler.is_private_file:
            PublicMachineTokenFile(self._rd).delete()
        else:
            UAFile(self._rd, self._fn).delete()
        self._machine_token = None
        self._entitlements = None
        self.file_handler = None

    @property
    def machine_token(self):
        """Return the machine-token if cached in the machine token response."""
        if not self._machine_token:
            if not self.file_handler:
                return None
            content = self.file_handler.read()
            try:
                content = content.replace("'", '"')
                self._machine_token = json.loads(
                    content, cls=util.DatetimeAwareJSONDecoder
                )
            except Exception:
                self._machine_token = content
        return self._machine_token

    @property
    def accounts(self):
        if bool(self.machine_token):
            account_info = self.machine_token["machineTokenInfo"][
                "accountInfo"
            ]
            return [account_info]
        return []

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
