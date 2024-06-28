import json
from datetime import datetime
from typing import Any, Dict, Optional

from uaclient import defaults, exceptions, system, util
from uaclient.contract_data_types import PublicMachineTokenData
from uaclient.files.files import UAFile

_machine_token_file = None


class MachineTokenFile:
    def __init__(
        self,
        directory: str = defaults.DEFAULT_DATA_DIR,
        machine_token_overlay_path: Optional[str] = None,
    ):
        file_name = defaults.MACHINE_TOKEN_FILE
        self.private_file = UAFile(
            file_name, directory + "/" + defaults.PRIVATE_SUBDIR
        )
        self.public_file = UAFile(file_name, directory, False)
        self.machine_token_overlay_path = machine_token_overlay_path
        self._machine_token = None  # type: Optional[Dict[str, Any]]
        self._entitlements = None
        self._contract_expiry_datetime = None

    def write(self, private_content: dict):
        """Update the machine_token file for both pub/private files"""
        if util.we_are_currently_root():
            private_content_str = json.dumps(
                private_content, cls=util.DatetimeAwareJSONEncoder
            )
            self.private_file.write(private_content_str)

            # PublicMachineTokenData only has public fields defined and
            # ignores all other (private) fields in from_dict
            public_content = PublicMachineTokenData.from_dict(
                private_content
            ).to_dict(keep_none=False)
            public_content_str = json.dumps(
                public_content, cls=util.DatetimeAwareJSONEncoder
            )
            self.public_file.write(public_content_str)

            self._machine_token = None
            self._entitlements = None
            self._contract_expiry_datetime = None
        else:
            raise exceptions.NonRootUserError()

    def delete(self):
        """Delete both pub and private files"""
        if util.we_are_currently_root():
            self.public_file.delete()
            self.private_file.delete()

            self._machine_token = None
            self._entitlements = None
            self._contract_expiry_datetime = None
        else:
            raise exceptions.NonRootUserError()

    def read(self) -> Optional[dict]:
        if util.we_are_currently_root():
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
        if util.we_are_currently_root():
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

    @property
    def contract_name(self) -> Optional[str]:
        if self.machine_token:
            return (
                self.machine_token.get("machineTokenInfo", {})
                .get("contractInfo", {})
                .get("name")
            )

        return None

    def parse_machine_token_overlay(self, machine_token_overlay_path):
        machine_token_overlay_content = system.load_file(
            machine_token_overlay_path
        )
        return json.loads(
            machine_token_overlay_content,
            cls=util.DatetimeAwareJSONDecoder,
        )

    @property
    def account(self) -> Dict[str, Any]:
        if bool(self.machine_token):
            return self.machine_token["machineTokenInfo"]["accountInfo"]
        return {}

    def entitlements(self, series: Optional[str] = None):
        """Return configured entitlements keyed by entitlement named"""
        if self._entitlements:
            return self._entitlements
        if not self.machine_token:
            return {}
        self._entitlements = self.get_entitlements_from_token(
            self.machine_token, series
        )
        return self._entitlements

    @staticmethod
    def get_entitlements_from_token(
        machine_token: Dict[str, Any], series: Optional[str] = None
    ):
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
            apply_contract_overrides(entitlement_cfg, series=series)
            entitlements[entitlement_name] = entitlement_cfg
        return entitlements

    @property
    def contract_expiry_datetime(self) -> Optional[datetime]:
        """Return a datetime of the attached contract expiration."""
        if not self._contract_expiry_datetime and self.is_attached:
            self._contract_expiry_datetime = (
                self.machine_token.get("machineTokenInfo", {})
                .get("contractInfo", {})
                .get("effectiveTo", None)
            )

        return self._contract_expiry_datetime

    @property
    def is_attached(self):
        """Report whether this machine configuration is attached to UA."""
        return bool(self.machine_token)  # machine_token is removed on detach

    @property
    def contract_remaining_days(self) -> Optional[int]:
        """Report num days until contract expiration based on effectiveTo

        :return: A positive int representing the number of days the attached
            contract remains in effect. Return a negative int for the number
            of days beyond contract's effectiveTo date.
        """
        if self.contract_expiry_datetime is None:
            return None
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

    @property
    def resource_tokens(self):
        if self.machine_token:
            return self.machine_token.get("resourceTokens", [])

        return None


def get_machine_token_file(cfg=None) -> MachineTokenFile:
    from uaclient.config import UAConfig

    global _machine_token_file

    if not _machine_token_file:
        if not cfg:
            cfg = UAConfig()

        _machine_token_file = MachineTokenFile(
            directory=cfg.data_dir,
            machine_token_overlay_path=cfg.features.get(
                "machine_token_overlay"
            ),
        )

    return _machine_token_file
