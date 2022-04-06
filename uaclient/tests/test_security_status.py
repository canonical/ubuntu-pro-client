from typing import List, Optional

import mock
import pytest

from uaclient.security_status import (
    UpdateStatus,
    filter_security_updates,
    get_origin_for_package,
    get_service_name,
    get_ua_info,
    get_update_status,
    security_status,
)

M_PATH = "uaclient.security_status."


def mock_origin(
    component: str, archive: str, origin: str, site: str
) -> mock.MagicMock:
    mock_origin = mock.MagicMock()
    mock_origin.component = component
    mock_origin.archive = archive
    mock_origin.origin = origin
    mock_origin.site = site
    return mock_origin


def mock_version(
    version: str, origin_list: List[mock.MagicMock] = []
) -> mock.MagicMock:
    mock_version = mock.MagicMock()
    mock_version.__gt__ = lambda self, other: self.version > other.version
    mock_version.version = version
    mock_version.origins = origin_list
    return mock_version


def mock_package(
    name: str,
    installed_version: Optional[mock.MagicMock] = None,
    other_versions: List[mock.MagicMock] = [],
):
    mock_package = mock.MagicMock()
    mock_package.name = name
    mock_package.versions = []
    mock_package.is_installed = bool(installed_version)

    if installed_version:
        mock_package.installed = installed_version
        installed_version.package = mock_package
        mock_package.versions.append(installed_version)

    for version in other_versions:
        version.package = mock_package
        mock_package.versions.append(version)

    if mock_package.versions:
        mock_package.candidate = max(mock_package.versions)

    return mock_package


MOCK_ORIGINS = {
    "now": mock_origin("now", "now", "", ""),
    "third-party": mock_origin("main", "", "other", "some.other.site"),
    "infra": mock_origin(
        "main", "example-infra-security", "UbuntuESM", "esm.ubuntu.com"
    ),
    "apps": mock_origin(
        "main", "example-apps-security", "UbuntuESMApps", "esm.ubuntu.com"
    ),
    "standard-security": mock_origin(
        "main", "example-security", "Ubuntu", "security.ubuntu.com"
    ),
    "archive_main": mock_origin(
        "main", "example-updates", "Ubuntu", "archive.ubuntu.com"
    ),
    "archive_universe": mock_origin(
        "universe", "example-updates", "Ubuntu", "archive.ubuntu.com"
    ),
}

ORIGIN_TO_SERVICE_MOCK = {
    ("UbuntuESM", "example-infra-security"): "esm-infra",
    ("Ubuntu", "example-security"): "standard-security",
    ("UbuntuESMApps", "example-apps-security"): "esm-apps",
}


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

    @pytest.mark.parametrize(
        "installed_version,other_versions,expected_output",
        (
            (mock_version("1.0", [MOCK_ORIGINS["now"]]), [], "unknown"),
            (
                mock_version("2.0", [MOCK_ORIGINS["now"]]),
                [mock_version("1.0", [MOCK_ORIGINS["archive_main"]])],
                "unknown",
            ),
            (
                mock_version("2.0", [MOCK_ORIGINS["now"]]),
                [mock_version("3.0", [MOCK_ORIGINS["archive_main"]])],
                "main",
            ),
            (
                mock_version(
                    "1.0", [MOCK_ORIGINS["infra"], MOCK_ORIGINS["now"]]
                ),
                [],
                "esm-infra",
            ),
            (
                mock_version(
                    "1.0", [MOCK_ORIGINS["apps"], MOCK_ORIGINS["now"]]
                ),
                [],
                "esm-apps",
            ),
            (
                mock_version(
                    "1.0", [MOCK_ORIGINS["archive_main"], MOCK_ORIGINS["now"]]
                ),
                [],
                "main",
            ),
            (
                mock_version(
                    "1.0",
                    [MOCK_ORIGINS["archive_universe"], MOCK_ORIGINS["now"]],
                ),
                [],
                "universe",
            ),
            (
                mock_version(
                    "1.0", [MOCK_ORIGINS["third-party"], MOCK_ORIGINS["now"]]
                ),
                [],
                "third-party",
            ),
        ),
    )
    def test_get_origin_for_package(
        self, installed_version, other_versions, expected_output
    ):
        package_mock = mock_package(
            "example", installed_version, other_versions
        )
        with mock.patch(
            M_PATH + "ORIGIN_INFORMATION_TO_SERVICE",
            ORIGIN_TO_SERVICE_MOCK,
        ):
            assert expected_output == get_origin_for_package(package_mock)

    @pytest.mark.parametrize(
        "origins_input,expected_output",
        (
            ([], ("", "")),
            ([MOCK_ORIGINS["now"]], ("", "")),
            ([MOCK_ORIGINS["third-party"], MOCK_ORIGINS["now"]], ("", "")),
            (
                [MOCK_ORIGINS["infra"], MOCK_ORIGINS["now"]],
                ("esm-infra", "esm.ubuntu.com"),
            ),
            (
                [MOCK_ORIGINS["apps"], MOCK_ORIGINS["now"]],
                ("esm-apps", "esm.ubuntu.com"),
            ),
            (
                [MOCK_ORIGINS["standard-security"], MOCK_ORIGINS["now"]],
                ("standard-security", "security.ubuntu.com"),
            ),
        ),
    )
    def test_service_name(self, origins_input, expected_output):
        with mock.patch(
            M_PATH + "ORIGIN_INFORMATION_TO_SERVICE",
            ORIGIN_TO_SERVICE_MOCK,
        ):
            assert expected_output == get_service_name(origins_input)

    def test_filter_security_updates(self):
        expected_return = [
            mock_version("2.0", [MOCK_ORIGINS["infra"]]),
            mock_version("2.0", [MOCK_ORIGINS["standard-security"]]),
            mock_version("3.0", [MOCK_ORIGINS["apps"]]),
        ]
        package_list = [
            mock_package(name="not-installed"),
            mock_package(
                name="there-is-no-update",
                installed_version=mock_version(
                    "1.0", [MOCK_ORIGINS["now"], MOCK_ORIGINS["archive_main"]]
                ),
            ),
            mock_package(
                name="latest-is-installed",
                installed_version=mock_version(
                    "2.0", [MOCK_ORIGINS["now"], MOCK_ORIGINS["infra"]]
                ),
                other_versions=[mock_version("1.0", [MOCK_ORIGINS["infra"]])],
            ),
            mock_package(
                name="update-available",
                installed_version=mock_version(
                    "1.0", [MOCK_ORIGINS["now"], MOCK_ORIGINS["archive_main"]]
                ),
                other_versions=[expected_return[0]],
            ),
            mock_package(
                name="not-a-security-update",
                installed_version=mock_version(
                    "1.0", [MOCK_ORIGINS["now"], MOCK_ORIGINS["archive_main"]]
                ),
                other_versions=[
                    mock_version("2.0", [MOCK_ORIGINS["archive_main"]])
                ],
            ),
            mock_package(
                name="more-than-one-update",
                installed_version=mock_version(
                    "1.0", [MOCK_ORIGINS["now"], MOCK_ORIGINS["archive_main"]]
                ),
                other_versions=[expected_return[1], expected_return[2]],
            ),
        ]
        with mock.patch(
            M_PATH + "ORIGIN_INFORMATION_TO_SERVICE",
            ORIGIN_TO_SERVICE_MOCK,
        ):
            filtered_versions = filter_security_updates(package_list)
            assert expected_return == filtered_versions
            assert [
                "update-available",
                "more-than-one-update",
                "more-than-one-update",
            ] == [v.package.name for v in filtered_versions]

    @mock.patch(M_PATH + "UAConfig.status", return_value={"attached": False})
    @mock.patch(
        M_PATH + "get_service_name",
        return_value=("esm-infra", "some.url.for.esm"),
    )
    @mock.patch(M_PATH + "get_origin_for_package", return_value="main")
    @mock.patch(M_PATH + "filter_security_updates")
    @mock.patch(M_PATH + "Cache")
    def test_security_status_format(
        self,
        m_cache,
        m_filter_sec_updates,
        _m_get_origin,
        _m_service_name,
        _m_status,
        FakeConfig,
    ):
        """Make sure the output format matches the expected JSON"""
        cfg = FakeConfig()
        m_version = mock_version("1.0")
        m_package = mock_package("example_package", m_version)

        m_cache.return_value = [m_package] * 10
        m_filter_sec_updates.return_value = [m_version] * 2

        expected_output = {
            "_schema_version": "0.1",
            "updates": [
                {
                    "package": "example_package",
                    "version": "1.0",
                    "service_name": "esm-infra",
                    "status": "pending_attach",
                    "origin": "some.url.for.esm",
                },
                {
                    "package": "example_package",
                    "version": "1.0",
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
                "num_installed_packages": 10,
                "num_installed_packages_main": 10,
                "num_installed_packages_restricted": 0,
                "num_installed_packages_universe": 0,
                "num_installed_packages_multiverse": 0,
                "num_installed_packages_third_party": 0,
                "num_installed_packages_unknown": 0,
                "num_esm_infra_updates": 2,
                "num_esm_apps_updates": 0,
                "num_esm_infra_packages": 0,
                "num_esm_apps_packages": 0,
                "num_standard_security_updates": 0,
            },
        }

        assert expected_output == security_status(cfg)
