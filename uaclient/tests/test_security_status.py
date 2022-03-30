from typing import List, Tuple

import mock
import pytest

from uaclient.security_status import (
    UpdateStatus,
    get_ua_info,
    get_update_status,
    security_status,
)

M_PATH = "uaclient.security_status."


# Each candidate/installed is a tuple of (version, archive, origin, site)
def mock_package(
    name,
    installed: Tuple[str, str, str, str] = None,
    candidates: List[Tuple[str, str, str, str]] = [],
):
    mock_package = mock.MagicMock()
    mock_package.name = name
    mock_package.versions = []
    mock_package.is_installed = bool(installed)

    if installed:
        mock_installed = mock.MagicMock()
        mock_installed.__gt__ = (
            lambda self, other: self.version > other.version
        )
        mock_installed.version = installed[0]

        mock_origin = mock.MagicMock()
        mock_origin.archive = installed[1]
        mock_origin.origin = installed[2]
        mock_origin.site = installed[3]
        mock_installed.origins = [mock_origin]

        mock_package.installed = mock_installed
        mock_package.versions.append(mock_installed)

    for candidate in candidates:
        mock_candidate = mock.MagicMock()
        mock_candidate.__gt__ = (
            lambda self, other: self.version > other.version
        )

        mock_candidate.package = mock_package
        mock_candidate.version = candidate[0]

        mock_origin = mock.MagicMock()
        mock_origin.archive = candidate[1]
        mock_origin.origin = candidate[2]
        mock_origin.site = candidate[3]
        mock_candidate.origins = [mock_origin]

        mock_package.versions.append(mock_candidate)

    return mock_package


class TestSecurityStatus:
    @pytest.mark.parametrize(
        "service_name,ua_info,expected_result",
        (
            ("standard-security", {}, UpdateStatus.AVAILABLE.value),
            (
                "esm",
                {"attached": True, "enabled_services": ["esm"]},
                UpdateStatus.AVAILABLE.value,
            ),
            ("esm", {"attached": False}, UpdateStatus.UNATTACHED.value),
            (
                "esm",
                {
                    "attached": True,
                    "enabled_services": ["not-esm"],
                    "entitled_services": ["esm"],
                },
                UpdateStatus.NOT_ENABLED.value,
            ),
            (
                "esm",
                {
                    "attached": True,
                    "enabled_services": ["not-esm"],
                    "entitled_services": ["not-esm-again"],
                },
                UpdateStatus.UNAVAILABLE.value,
            ),
        ),
    )
    def test_get_update_status(self, service_name, ua_info, expected_result):
        assert get_update_status(service_name, ua_info) == expected_result

    @pytest.mark.parametrize("is_attached", (True, False))
    @mock.patch(M_PATH + "UAConfig.status")
    def test_get_ua_info(self, m_status, is_attached, FakeConfig):
        if is_attached:
            cfg = FakeConfig().for_attached_machine()
        else:
            cfg = FakeConfig()

        m_status.return_value = {
            "attached": is_attached,
            "services": [
                {"name": "esm-infra", "entitled": "yes", "status": "enabled"},
                {"name": "esm-apps", "entitled": "yes", "status": "disabled"},
                {
                    "name": "non-esm-service",
                    "entitled": "yes",
                    "status": "enabled",
                },
            ],
        }

        result = get_ua_info(cfg)

        if is_attached:
            assert result == {
                "attached": True,
                "enabled_services": ["esm-infra"],
                "entitled_services": ["esm-infra", "esm-apps"],
            }
        else:
            assert result == {
                "attached": False,
                "enabled_services": [],
                "entitled_services": [],
            }

    @mock.patch(M_PATH + "UAConfig.status", return_value={"attached": False})
    @mock.patch(M_PATH + "Cache")
    def test_finds_updates_for_installed_packages(
        self, m_cache, _m_status, FakeConfig
    ):
        m_cache.return_value = [
            mock_package(name="not_installed"),
            mock_package(
                name="there_is_no_update",
                installed=("1.0", "somewhere", "somehow", ""),
            ),
            mock_package(
                name="latest_is_installed",
                installed=("2.0", "standard-packages", "Ubuntu", ""),
                candidates=[
                    (
                        "1.0",
                        "example-infra-security",
                        "UbuntuESM",
                        "some.url.for.esm",
                    )
                ],
            ),
            mock_package(
                name="update_available",
                # this is an ESM-INFRA example for the counters
                installed=("1.0", "example-infra-security", "UbuntuESM", ""),
                candidates=[
                    (
                        "2.0",
                        "example-infra-security",
                        "UbuntuESM",
                        "some.url.for.esm",
                    )
                ],
            ),
            mock_package(
                name="not_a_security_update",
                installed=("1.0", "somewhere", "somehow", ""),
                candidates=[
                    (
                        "2.0",
                        "example-notsecurity",
                        "NotUbuntuESM",
                        "some.url.for.esm",
                    )
                ],
            ),
            mock_package(
                name="more_than_one_update_available",
                installed=("1.0", "somewhere", "somehow", ""),
                candidates=[
                    (
                        "2.0",
                        "example-security",
                        "Ubuntu",
                        "some.url.for.standard",
                    ),
                    (
                        "3.0",
                        "example-infra-security",
                        "UbuntuESM",
                        "some.url.for.esm",
                    ),
                ],
            ),
        ]

        origin_to_service_dict = {
            ("UbuntuESM", "example-infra-security"): "esm-infra",
            ("Ubuntu", "example-security"): "standard-security",
            ("UbuntuESMApps", "example-apps-security"): "esm-apps",
        }

        cfg = FakeConfig()

        expected_output = {
            "_schema_version": "0.1",
            "packages": [
                {
                    "package": "update_available",
                    "version": "2.0",
                    "service_name": "esm-infra",
                    "status": "pending_attach",
                    "origin": "some.url.for.esm",
                },
                {
                    "package": "more_than_one_update_available",
                    "version": "2.0",
                    "service_name": "standard-security",
                    "status": "upgrade_available",
                    "origin": "some.url.for.standard",
                },
                {
                    "package": "more_than_one_update_available",
                    "version": "3.0",
                    "service_name": "esm-infra",
                    "status": "pending_attach",
                    "origin": "some.url.for.esm",
                },
            ],
            "summary": {
                "ua": {
                    "attached": False,
                    "enabled_services": [],
                    "entitled_services": [],
                },
                "num_installed_packages": 5,
                "num_esm_infra_updates": 2,
                "num_esm_apps_updates": 0,
                "num_esm_infra_packages": 1,
                "num_esm_apps_packages": 0,
                "num_standard_security_updates": 1,
            },
        }

        with mock.patch(
            M_PATH + "ORIGIN_INFORMATION_TO_SERVICE", origin_to_service_dict
        ):
            output = security_status(cfg)
        assert output == expected_output
