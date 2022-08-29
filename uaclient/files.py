import json
import logging
import os
import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, Optional, Type, TypeVar

import yaml

from uaclient import (
    data_types,
    defaults,
    event_logger,
    exceptions,
    messages,
    system,
    util,
)
from uaclient.contract_data_types import PublicMachineTokenData

event = event_logger.get_event_logger()
LOG = logging.getLogger(__name__)


class UAFile:
    def __init__(
        self,
        name: str,
        directory: str = defaults.DEFAULT_DATA_DIR,
        private: bool = True,
    ):
        self._directory = directory
        self._file_name = name
        self._is_private = private
        self._path = os.path.join(self._directory, self._file_name)

    @property
    def path(self) -> str:
        return self._path

    @property
    def is_private(self) -> bool:
        return self._is_private

    @property
    def is_present(self):
        return os.path.exists(self.path)

    def write(self, content: str):
        file_mode = (
            defaults.ROOT_READABLE_MODE
            if self.is_private
            else defaults.WORLD_READABLE_MODE
        )
        if not os.path.exists(self._directory):
            os.makedirs(self._directory)
            if os.path.basename(self._directory) == defaults.PRIVATE_SUBDIR:
                os.chmod(self._directory, 0o700)
        system.write_file(self.path, content, file_mode)

    def read(self) -> Optional[str]:
        content = None
        try:
            content = system.load_file(self.path)
        except FileNotFoundError:
            LOG.debug("File does not exist: {}".format(self.path))
        return content

    def delete(self):
        system.remove_file(self.path)


class DataObjectFileFormat(Enum):
    JSON = "json"
    YAML = "yaml"


DOFType = TypeVar("DOFType", bound=data_types.DataObject)


class DataObjectFile(Generic[DOFType]):
    def __init__(
        self,
        data_object_cls: Type[DOFType],
        ua_file: UAFile,
        file_format: DataObjectFileFormat = DataObjectFileFormat.JSON,
    ):
        self.data_object_cls = data_object_cls
        self.ua_file = ua_file
        self.file_format = file_format

    def read(self) -> Optional[DOFType]:
        raw_data = self.ua_file.read()
        if raw_data is None:
            return None

        parsed_data = None
        if self.file_format == DataObjectFileFormat.JSON:
            try:
                parsed_data = json.loads(raw_data)
            except json.JSONDecodeError:
                raise exceptions.InvalidFileFormatError(
                    self.ua_file.path, "json"
                )
        elif self.file_format == DataObjectFileFormat.YAML:
            try:
                parsed_data = yaml.safe_load(raw_data)
            except yaml.parser.ParserError:
                raise exceptions.InvalidFileFormatError(
                    self.ua_file.path, "yaml"
                )

        if parsed_data is None:
            return None

        return self.data_object_cls.from_dict(parsed_data)

    def write(self, content: DOFType):
        if self.file_format == DataObjectFileFormat.JSON:
            str_content = content.to_json()
        elif self.file_format == DataObjectFileFormat.YAML:
            data = content.to_dict()
            str_content = yaml.dump(data, default_flow_style=False)

        self.ua_file.write(str_content)


class MachineTokenFile:
    def __init__(
        self,
        directory: str = defaults.DEFAULT_DATA_DIR,
        root_mode: bool = True,
        machine_token_overlay_path: Optional[str] = None,
    ):
        file_name = defaults.MACHINE_TOKEN_FILE
        self.is_root = root_mode
        self.private_file = UAFile(
            file_name, directory + defaults.PRIVATE_SUBDIR
        )
        self.public_file = UAFile(file_name, directory, False)
        self.machine_token_overlay_path = machine_token_overlay_path
        self._machine_token = None
        self._entitlements = None
        self._contract_expiry_datetime = None

    def write(self, content: dict):
        """Update the machine_token file for both pub/private files"""
        if self.is_root:
            content_str = json.dumps(
                content, cls=util.DatetimeAwareJSONEncoder
            )
            self.private_file.write(content_str)
            content = json.loads(content_str)  # taking care of datetime type
            content = PublicMachineTokenData.from_dict(content).to_dict(False)
            content_str = json.dumps(
                content, cls=util.DatetimeAwareJSONEncoder
            )
            self.public_file.write(content_str)

            self._machine_token = None
            self._entitlements = None
        else:
            raise exceptions.NonRootUserError()

    def delete(self):
        """Delete both pub and private files"""
        if self.is_root:
            self.public_file.delete()
            self.private_file.delete()

            self._machine_token = None
            self._entitlements = None
        else:
            raise exceptions.NonRootUserError()

    def read(self) -> Optional[dict]:
        if self.is_root:
            file_handler = self.private_file
        else:
            file_handler = self.public_file
        content = file_handler.read()
        if not content:
            return None
        try:
            content = json.loads(content, cls=util.DatetimeAwareJSONDecoder)
        except Exception:
            pass
        return content  # type: ignore

    @property
    def is_present(self):
        if self.is_root:
            return self.public_file.is_present and self.private_file.is_present
        else:
            return self.public_file.is_present

    @property
    def machine_token(self):
        """Return the machine-token if cached in the machine token response."""
        if not self._machine_token:
            content = self.read()
            if content and self.machine_token_overlay_path:
                machine_token_overlay = self.parse_machine_token_overlay(
                    self.machine_token_overlay_path
                )

                if machine_token_overlay:
                    util.depth_first_merge_overlay_dict(
                        base_dict=content,
                        overlay_dict=machine_token_overlay,
                    )
            self._machine_token = content
        return self._machine_token

    def parse_machine_token_overlay(self, machine_token_overlay_path):
        if not os.path.exists(machine_token_overlay_path):
            raise exceptions.UserFacingError(
                messages.INVALID_PATH_FOR_MACHINE_TOKEN_OVERLAY.format(
                    file_path=machine_token_overlay_path
                )
            )

        try:
            machine_token_overlay_content = system.load_file(
                machine_token_overlay_path
            )

            return json.loads(
                machine_token_overlay_content,
                cls=util.DatetimeAwareJSONDecoder,
            )
        except ValueError as e:
            raise exceptions.UserFacingError(
                messages.ERROR_JSON_DECODING_IN_FILE.format(
                    error=str(e), file_path=machine_token_overlay_path
                )
            )

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
        from uaclient.contract import apply_contract_overrides

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
            apply_contract_overrides(entitlement_cfg)
            entitlements[entitlement_name] = entitlement_cfg
        return entitlements

    @property
    def contract_expiry_datetime(self) -> datetime:
        """Return a datetime of the attached contract expiration."""
        if not self._contract_expiry_datetime:
            self._contract_expiry_datetime = self.machine_token[
                "machineTokenInfo"
            ]["contractInfo"]["effectiveTo"]

        return self._contract_expiry_datetime  # type: ignore

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


class NoticeFile:
    def __init__(
        self,
        directory: str = defaults.DEFAULT_DATA_DIR,
        root_mode: bool = True,
    ):
        file_name = "notices.json"
        self.file = UAFile(file_name, directory, False)
        self.is_root = root_mode

    def add(self, label: str, description: str):
        """
        Adds a notice to the notices.json file.
        Raises a NonRootUserError if the user is not root.
        """
        if self.is_root:
            notices = self.read() or []
            notice = [label, description]
            if notice not in notices:
                notices.append(notice)
                self.write(notices)
        else:
            raise exceptions.NonRootUserError

    def try_add(self, label: str, description: str):
        """
        Adds a notice to the notices.json file.
        Logs a warning when adding as non-root
        """
        try:
            self.add(label, description)
        except exceptions.NonRootUserError:
            event.warning("Trying to add notice as non-root user")

    def remove(self, label_regex: str, descr_regex: str):
        """
        Removes a notice to the notices.json file.
        Raises a NonRootUserError if the user is not root.
        """
        if self.is_root:
            notices = []
            cached_notices = self.read() or []
            if cached_notices:
                for notice_label, notice_descr in cached_notices:
                    if re.match(label_regex, notice_label):
                        if re.match(descr_regex, notice_descr):
                            continue
                    notices.append((notice_label, notice_descr))
            if notices:
                self.write(notices)
            elif os.path.exists(self.file.path):
                self.file.delete()
        else:
            raise exceptions.NonRootUserError

    def try_remove(self, label_regex: str, descr_regex: str):
        """
        Removes a notice to the notices.json file.
        Logs  a warning when removing as non-root
        """
        try:
            self.remove(label_regex, descr_regex)
        except exceptions.NonRootUserError:
            event.warning("Trying to remove notice as non-root user")

    def read(self):
        content = self.file.read()
        if not content:
            return None
        try:
            return json.loads(content, cls=util.DatetimeAwareJSONDecoder)
        except ValueError:
            return content

    def write(self, content: Any):
        if not isinstance(content, str):
            content = json.dumps(content, cls=util.DatetimeAwareJSONEncoder)
        self.file.write(content)
