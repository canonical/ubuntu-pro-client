import mock
import pytest

from uaclient.security_status import (
    ServiceStatus,
    UpdateStatus,
    get_ua_info,
    get_update_status,
    security_status,
)

M_PATH = "uaclient.security_status."


def mock_package(
    name, installed=None, candidate=None, archive=None, origin=None
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
        mock_installed.version = installed

        mock_package.installed = mock_installed
        mock_package.versions.append(mock_installed)

    if candidate:
        mock_candidate = mock.MagicMock()
        mock_candidate.__gt__ = (
            lambda self, other: self.version > other.version
        )

        mock_candidate.version = candidate

        mock_origin = mock.MagicMock()
        mock_origin.archive = archive
        mock_origin.origin = origin
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
    @mock.patch(M_PATH + "get_service_status")
    def test_get_ua_info(self, m_service_status, is_attached, FakeConfig):
        if is_attached:
            cfg = FakeConfig().for_attached_machine()
        else:
            cfg = FakeConfig()

        def service_status_side_effect(_cfg, service):
            if service == "esm-infra":
                return ServiceStatus(True, True)
            return ServiceStatus(True, False)

        m_service_status.side_effect = service_status_side_effect

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

    @mock.patch(
        M_PATH + "get_platform_info", return_value={"series": "example"}
    )
    @mock.patch(M_PATH + "Cache")
    def test_finds_updates_for_installed_packages(
        self, m_cache, _m_platform_info, FakeConfig
    ):
        m_cache.return_value = [
            mock_package(name="not_installed"),
            mock_package(name="there_is_no_update", installed="1.0"),
            mock_package(
                name="latest_is_installed",
                installed="2.0",
                candidate="1.0",
                archive="example-infra-security",
                origin="UbuntuESM",
            ),
            mock_package(
                name="update_available",
                installed="1.0",
                candidate="2.0",
                archive="example-infra-security",
                origin="UbuntuESM",
            ),
        ]

        cfg = FakeConfig()

        expected_output = {
            "_schema_version": "0",
            "packages": [
                {
                    "package": "update_available",
                    "version": "2.0",
                    "service_name": "esm-infra",
                    "status": "pending_attach",
                }
            ],
            "summary": {
                "ua": {
                    "attached": False,
                    "enabled_services": [],
                    "entitled_services": [],
                },
                "num_installed_packages": 3,
                "num_esm_infra_updates": 1,
                "num_esm_apps_updates": 0,
                "num_standard_security_updates": 0,
            },
        }

        output = security_status(cfg)
        assert output == expected_output
