import copy
import json

import mock
import pytest

from uaclient.entitlements import valid_services
from uaclient.files.machine_token import MachineTokenFile


@pytest.fixture
def all_resources_available(FakeConfig):
    resources = [
        {"name": name, "available": True}
        for name in valid_services(cfg=FakeConfig())
    ]
    return resources


class TestAccounts:
    @mock.patch("uaclient.files.machine_token.MachineTokenFile.read")
    def test_accounts_returns_none_when_no_cached_account_value(
        self, m_machine_token_read, all_resources_available
    ):
        """Config.accounts property returns an empty list when no cache."""
        machine_token_file = MachineTokenFile()
        m_machine_token_read.return_value = None
        assert machine_token_file.account == {}

    @pytest.mark.usefixtures("all_resources_available")
    def test_accounts_extracts_account_key_from_machine_token_cache(
        self, all_resources_available, tmpdir, FakeConfig
    ):
        """Use machine_token cached accountInfo when no accounts cache."""
        machine_token_file = MachineTokenFile()
        accountInfo = {"id": "1", "name": "accountname"}

        machine_token_file._machine_token = {
            "availableResources": all_resources_available,
            "machineTokenInfo": {"accountInfo": accountInfo},
        }

        assert accountInfo == machine_token_file.account


class TestMachineTokenOverlay:
    machine_token_dict = {
        "availableResources": [
            {"available": False, "name": "cc-eal"},
            {"available": True, "name": "esm-infra"},
            {"available": False, "name": "fips"},
        ],
        "machineTokenInfo": {
            "contractInfo": {
                "resourceEntitlements": [
                    {
                        "type": "cc-eal",
                        "entitled": False,
                        "affordances": {
                            "architectures": [
                                "amd64",
                                "ppc64el",
                                "ppc64le",
                                "s390x",
                                "x86_64",
                            ],
                            "series": ["xenial"],
                        },
                        "directives": {
                            "additionalPackages": ["ubuntu-commoncriteria"],
                            "aptKey": "key",
                            "aptURL": "https://esm.ubuntu.com/cc",
                            "suites": ["xenial"],
                        },
                    },
                    {
                        "type": "livepatch",
                        "entitled": True,
                        "affordances": {
                            "architectures": ["amd64", "x86_64"],
                            "tier": "stable",
                        },
                        "directives": {
                            "caCerts": "",
                            "remoteServer": "https://livepatch.canonical.com",
                        },
                        "obligations": {"enableByDefault": True},
                    },
                ]
            }
        },
    }

    @mock.patch("uaclient.system.load_file")
    @mock.patch("uaclient.files.machine_token.MachineTokenFile.read")
    @mock.patch("uaclient.config.os.path.exists", return_value=True)
    def test_machine_token_update_with_overlay(
        self, m_path, m_token_read, m_load_file, FakeConfig
    ):
        m_token_read.return_value = self.machine_token_dict

        remote_server_overlay = "overlay"
        json_str = json.dumps(
            {
                "availableResources": [
                    {"available": False, "name": "esm-infra"},
                    {"available": True, "name": "test-overlay"},
                ],
                "machineTokenInfo": {
                    "contractInfo": {
                        "resourceEntitlements": [
                            {
                                "type": "livepatch",
                                "entitled": False,
                                "affordances": {"architectures": ["test"]},
                                "directives": {"remoteServer": "overlay"},
                            }
                        ]
                    }
                },
            }
        )
        m_load_file.return_value = json_str

        expected = copy.deepcopy(self.machine_token_dict)
        expected["machineTokenInfo"]["contractInfo"]["resourceEntitlements"][
            1
        ]["directives"]["remoteServer"] = remote_server_overlay
        expected["machineTokenInfo"]["contractInfo"]["resourceEntitlements"][
            1
        ]["affordances"]["architectures"] = ["test"]
        expected["machineTokenInfo"]["contractInfo"]["resourceEntitlements"][
            1
        ]["entitled"] = False
        expected["availableResources"][1]["available"] = False
        expected["availableResources"].append(
            {"available": True, "name": "test-overlay"}
        )

        machine_token_file = MachineTokenFile(
            machine_token_overlay_path="test"
        )
        assert expected == machine_token_file.machine_token

    @mock.patch("uaclient.files.machine_token.MachineTokenFile.read")
    def test_machine_token_without_overlay(self, m_token_read, FakeConfig):
        m_token_read.return_value = self.machine_token_dict
        machine_token_file = MachineTokenFile()
        assert self.machine_token_dict == machine_token_file.machine_token


class TestEntitlements:
    def test_entitlements_property_keyed_by_entitlement_name(
        self, all_resources_available
    ):
        """Return machine_token resourceEntitlements, keyed by name."""
        machine_token_file = MachineTokenFile()
        machine_token_file._machine_token = {
            "availableResources": all_resources_available,
            "machineTokenInfo": {
                "contractInfo": {
                    "resourceEntitlements": [
                        {"type": "entitlement1", "entitled": True},
                        {"type": "entitlement2", "entitled": True},
                    ]
                }
            },
        }
        expected = {
            "entitlement1": {
                "entitlement": {"entitled": True, "type": "entitlement1"}
            },
            "entitlement2": {
                "entitlement": {"entitled": True, "type": "entitlement2"}
            },
        }
        assert expected == machine_token_file.entitlements()

    def test_entitlements_uses_resource_token_from_machine_token(
        self, all_resources_available
    ):
        """Include entitlement-specific resourceTokens from machine_token"""
        machine_token_file = MachineTokenFile()
        machine_token_file._machine_token = {
            "availableResources": all_resources_available,
            "machineTokenInfo": {
                "contractInfo": {
                    "resourceEntitlements": [
                        {"type": "entitlement1", "entitled": True},
                        {"type": "entitlement2", "entitled": True},
                    ]
                }
            },
            "resourceTokens": [
                {"type": "entitlement1", "token": "ent1-token"},
                {"type": "entitlement2", "token": "ent2-token"},
            ],
        }
        expected = {
            "entitlement1": {
                "entitlement": {"entitled": True, "type": "entitlement1"},
                "resourceToken": "ent1-token",
            },
            "entitlement2": {
                "entitlement": {"entitled": True, "type": "entitlement2"},
                "resourceToken": "ent2-token",
            },
        }
        assert expected == machine_token_file.entitlements()
