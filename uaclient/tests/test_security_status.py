import logging
from collections import defaultdict
from json import JSONDecodeError
from typing import List, Optional

import mock
import pytest

from uaclient.exceptions import ProcessExecutionError
from uaclient.security_status import (
    RebootStatus,
    UpdateStatus,
    filter_security_updates,
    get_livepatch_fixed_cves,
    get_origin_for_package,
    get_reboot_status,
    get_ua_info,
    get_update_status,
    security_status_dict,
)
from uaclient.system import KernelInfo

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
    version: str,
    origin_list: List[mock.MagicMock] = [],
    size: int = 1,
) -> mock.MagicMock:
    mock_version = mock.MagicMock()
    mock_version.__gt__ = lambda self, other: self.version > other.version
    mock_version.version = version
    mock_version.origins = origin_list
    mock_version.size = size
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

    mock_package.installed = None
    if installed_version:
        mock_package.installed = installed_version
        installed_version.package = mock_package
        mock_package.versions.append(installed_version)

    for version in other_versions:
        version.package = mock_package
        mock_package.versions.append(version)

    mock_package.candidate = None
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
    "archive_backports": mock_origin(
        "universe", "example-backports", "Ubuntu", "archive.ubuntu.com"
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
    @mock.patch("uaclient.security_status.status")
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
            M_PATH + "get_origin_information_to_service_map",
            return_value=ORIGIN_TO_SERVICE_MOCK,
        ):
            assert expected_output == get_origin_for_package(package_mock)

    @mock.patch("uaclient.security_status.get_esm_cache", return_value={})
    def test_filter_security_updates(self, _m_get_esm_cache):
        expected_return = defaultdict(
            list,
            {
                "esm-infra": [
                    (
                        mock_version("2.0", [MOCK_ORIGINS["infra"]]),
                        "esm.ubuntu.com",
                    )
                ],
                "standard-security": [
                    (
                        mock_version(
                            "2.0", [MOCK_ORIGINS["standard-security"]]
                        ),
                        "security.ubuntu.com",
                    ),
                    (
                        mock_version(
                            "2.1", [MOCK_ORIGINS["standard-security"]]
                        ),
                        "security.ubuntu.com",
                    ),
                ],
                "esm-apps": [
                    (
                        mock_version("3.0", [MOCK_ORIGINS["apps"]]),
                        "esm.ubuntu.com",
                    )
                ],
                "standard-updates": [
                    (
                        mock_version("2.0", [MOCK_ORIGINS["archive_main"]]),
                        "archive.ubuntu.com",
                    )
                ],
            },
        )
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
                name="infra-update-available",
                installed_version=mock_version(
                    "1.0", [MOCK_ORIGINS["now"], MOCK_ORIGINS["archive_main"]]
                ),
                other_versions=[expected_return["esm-infra"][0][0]],
            ),
            mock_package(
                name="security-update-available",
                installed_version=mock_version(
                    "1.0", [MOCK_ORIGINS["now"], MOCK_ORIGINS["archive_main"]]
                ),
                other_versions=[
                    expected_return["standard-security"][0][0],
                ],
            ),
            mock_package(
                name="not-a-security-update",
                installed_version=mock_version(
                    "1.0", [MOCK_ORIGINS["now"], MOCK_ORIGINS["archive_main"]]
                ),
                other_versions=[expected_return["standard-updates"][0][0]],
            ),
            mock_package(
                name="more-than-one-update",
                installed_version=mock_version(
                    "1.0", [MOCK_ORIGINS["now"], MOCK_ORIGINS["archive_main"]]
                ),
                other_versions=[
                    expected_return["standard-security"][1][0],
                    expected_return["esm-apps"][0][0],
                ],
            ),
            mock_package(
                name="upgrade-is-backports-boo",
                installed_version=mock_version(
                    "1.0",
                    [MOCK_ORIGINS["now"], MOCK_ORIGINS["archive_universe"]],
                ),
                other_versions=[
                    mock_version("2.0", [MOCK_ORIGINS["archive_backports"]])
                ],
            ),
        ]
        with mock.patch(
            M_PATH + "get_origin_information_to_service_map",
            return_value=ORIGIN_TO_SERVICE_MOCK,
        ):
            filtered_versions = filter_security_updates(package_list)
            assert expected_return == filtered_versions
            assert (
                filtered_versions["esm-infra"][0][0].package.name
                == "infra-update-available"
            )
            assert (
                filtered_versions["standard-security"][0][0].package.name
                == "security-update-available"
            )
            assert (
                filtered_versions["standard-security"][1][0].package.name
                == "more-than-one-update"
            )
            assert (
                filtered_versions["esm-apps"][0][0].package.name
                == "more-than-one-update"
            )
            assert (
                filtered_versions["standard-updates"][0][0].package.name
                == "not-a-security-update"
            )

    @mock.patch("uaclient.security_status.get_esm_cache")
    def test_filter_security_updates_when_esm_disabled(self, m_esm_cache):
        expected_return = defaultdict(
            list,
            {
                "esm-infra": [
                    (
                        mock_version("2.0", [MOCK_ORIGINS["infra"]]),
                        "esm.ubuntu.com",
                    )
                ],
                "standard-security": [
                    (
                        mock_version(
                            "2.0", [MOCK_ORIGINS["standard-security"]]
                        ),
                        "security.ubuntu.com",
                    ),
                    (
                        mock_version(
                            "2.1", [MOCK_ORIGINS["standard-security"]]
                        ),
                        "security.ubuntu.com",
                    ),
                ],
                "esm-apps": [
                    (
                        mock_version("3.0", [MOCK_ORIGINS["apps"]]),
                        "esm.ubuntu.com",
                    )
                ],
                "standard-updates": [
                    (
                        mock_version("2.0", [MOCK_ORIGINS["archive_main"]]),
                        "archive.ubuntu.com",
                    )
                ],
            },
        )
        esm_package_list = {
            "infra-update-available": mock_package(
                name="infra-update-available",
                installed_version=mock_version(
                    "1.0", [MOCK_ORIGINS["now"], MOCK_ORIGINS["archive_main"]]
                ),
                other_versions=[expected_return["esm-infra"][0][0]],
            ),
            "update-multiple-caches": mock_package(
                name="update-multiple-caches",
                installed_version=mock_version(
                    "1.0", [MOCK_ORIGINS["now"], MOCK_ORIGINS["archive_main"]]
                ),
                other_versions=[
                    expected_return["esm-apps"][0][0],
                ],
            ),
        }

        package_list = [
            mock_package(name="not-installed"),
            mock_package(
                name="latest-is-installed",
                installed_version=mock_version(
                    "2.0", [MOCK_ORIGINS["now"], MOCK_ORIGINS["infra"]]
                ),
            ),
            mock_package(
                name="infra-update-available",
                installed_version=mock_version(
                    "1.0", [MOCK_ORIGINS["now"], MOCK_ORIGINS["archive_main"]]
                ),
            ),
            mock_package(
                name="there-is-no-update",
                installed_version=mock_version(
                    "1.0", [MOCK_ORIGINS["now"], MOCK_ORIGINS["archive_main"]]
                ),
            ),
            mock_package(
                name="security-update-available",
                installed_version=mock_version(
                    "1.0", [MOCK_ORIGINS["now"], MOCK_ORIGINS["archive_main"]]
                ),
                other_versions=[
                    expected_return["standard-security"][0][0],
                ],
            ),
            mock_package(
                name="not-a-security-update",
                installed_version=mock_version(
                    "1.0", [MOCK_ORIGINS["now"], MOCK_ORIGINS["archive_main"]]
                ),
                other_versions=[expected_return["standard-updates"][0][0]],
            ),
            mock_package(
                name="update-multiple-caches",
                installed_version=mock_version(
                    "1.0", [MOCK_ORIGINS["now"], MOCK_ORIGINS["archive_main"]]
                ),
                other_versions=[
                    expected_return["standard-security"][1][0],
                ],
            ),
            mock_package(
                name="upgrade-is-backports-boo",
                installed_version=mock_version(
                    "1.0",
                    [MOCK_ORIGINS["now"], MOCK_ORIGINS["archive_universe"]],
                ),
                other_versions=[
                    mock_version("2.0", [MOCK_ORIGINS["archive_backports"]])
                ],
            ),
        ]

        m_esm_cache.return_value = esm_package_list
        with mock.patch(
            M_PATH + "get_origin_information_to_service_map",
            return_value=ORIGIN_TO_SERVICE_MOCK,
        ):
            filtered_versions = filter_security_updates(package_list)
            assert expected_return == filtered_versions
            assert (
                filtered_versions["esm-infra"][0][0].package.name
                == "infra-update-available"
            )
            assert (
                filtered_versions["standard-security"][0][0].package.name
                == "security-update-available"
            )
            assert (
                filtered_versions["standard-security"][1][0].package.name
                == "update-multiple-caches"
            )
            assert (
                filtered_versions["esm-apps"][0][0].package.name
                == "update-multiple-caches"
            )
            assert (
                filtered_versions["standard-updates"][0][0].package.name
                == "not-a-security-update"
            )

    @mock.patch(M_PATH + "get_reboot_status")
    @mock.patch(M_PATH + "get_livepatch_fixed_cves", return_value=[])
    @mock.patch(M_PATH + "status", return_value={"attached": False})
    @mock.patch(M_PATH + "get_origin_for_package", return_value="main")
    @mock.patch(M_PATH + "filter_security_updates")
    @mock.patch(M_PATH + "apt.Cache")
    def test_security_status_dict(
        self,
        m_cache,
        m_filter_sec_updates,
        _m_get_origin,
        _m_status,
        _m_livepatch_cves,
        m_reboot_status,
        FakeConfig,
    ):
        """Make sure the output format matches the expected JSON"""
        cfg = FakeConfig()
        m_version = mock_version("1.0", size=123456)
        m_package = mock_package("example_package", m_version)

        m_cache.return_value = [m_package] * 10
        m_filter_sec_updates.return_value = {
            "esm-infra": [(m_version, "some.url.for.esm")] * 2,
            "esm-apps": [],
            "standard-security": [],
        }
        m_reboot_status.return_value = RebootStatus.REBOOT_NOT_REQUIRED

        expected_output = {
            "_schema_version": "0.1",
            "packages": [
                {
                    "package": "example_package",
                    "version": "1.0",
                    "service_name": "esm-infra",
                    "status": "pending_attach",
                    "origin": "some.url.for.esm",
                    "download_size": 123456,
                },
                {
                    "package": "example_package",
                    "version": "1.0",
                    "service_name": "esm-infra",
                    "status": "pending_attach",
                    "origin": "some.url.for.esm",
                    "download_size": 123456,
                },
            ],
            "summary": {
                "ua": {
                    "attached": False,
                    "enabled_services": [],
                    "entitled_services": [],
                },
                "num_installed_packages": 10,
                "num_main_packages": 10,
                "num_restricted_packages": 0,
                "num_universe_packages": 0,
                "num_multiverse_packages": 0,
                "num_third_party_packages": 0,
                "num_unknown_packages": 0,
                "num_esm_infra_packages": 0,
                "num_esm_apps_packages": 0,
                "num_esm_infra_updates": 2,
                "num_esm_apps_updates": 0,
                "num_standard_security_updates": 0,
                "reboot_required": "no",
            },
            "livepatch": {"fixed_cves": []},
        }

        assert expected_output == security_status_dict(cfg)


@mock.patch(M_PATH + "json.loads")
@mock.patch(M_PATH + "get_kernel_info")
class TestGetLivepatchFixedCVEs:
    @mock.patch(M_PATH + "subp")
    def test_livepatch_subp_error(self, m_subp, _m_kernel_info, _m_loads):
        m_subp.side_effect = ProcessExecutionError("error")

        assert [] == get_livepatch_fixed_cves()

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    def test_livepatch_wrong_json(self, _m_kernel_info, m_loads, caplog_text):
        m_loads.side_effect = JSONDecodeError("", "", 0)

        assert [] == get_livepatch_fixed_cves()
        assert "Could not parse Livepatch Status JSON" in caplog_text()

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    def test_cant_get_kernel_info(self, m_kernel_info, m_loads, caplog_text):
        m_loads.return_value = {
            "Status": [
                {
                    "Kernel": "installed-kernel-generic",
                    "Livepatch": {
                        "State": "nothing-to-apply",
                    },
                }
            ],
        }

        m_kernel_info.return_value = KernelInfo(
            uname_release="",
            proc_version_signature_version=None,
            major=None,
            minor=None,
            patch=None,
            abi=None,
            flavor=None,
        )

        assert [] == get_livepatch_fixed_cves()

    def test_livepatch_no_fixes(self, m_kernel_info, m_loads):
        m_kernel_info.return_value.proc_version_signature_version = (
            "installed-kernel-generic"
        )
        m_loads.return_value = {
            "Status": [
                {
                    "Kernel": "installed-kernel-generic",
                    "Livepatch": {
                        "State": "nothing-to-apply",
                    },
                }
            ],
        }

        assert [] == get_livepatch_fixed_cves()

    def test_livepatch_has_fixes(self, m_kernel_info, m_loads):
        m_kernel_info.return_value.proc_version_signature_version = (
            "installed-kernel-generic"
        )
        m_loads.return_value = {
            "Status": [
                {
                    "Kernel": "installed-kernel-generic",
                    "Livepatch": {
                        "State": "applied",
                        "Fixes": [
                            {
                                "Name": "cve-example",
                                "Description": "",
                                "Bug": "",
                                "Patched": True,
                            },
                        ],
                    },
                }
            ],
        }

        assert [
            {"name": "cve-example", "patched": True}
        ] == get_livepatch_fixed_cves()


class TestRebootStatus:
    @mock.patch("uaclient.security_status.should_reboot", return_value=False)
    def test_get_reboot_status_no_reboot_needed(self, m_should_reboot):
        assert get_reboot_status() == RebootStatus.REBOOT_NOT_REQUIRED
        assert 1 == m_should_reboot.call_count

    @mock.patch("uaclient.security_status.load_file")
    @mock.patch("uaclient.security_status.should_reboot", return_value=True)
    def test_get_reboot_status_no_reboot_pkgs_file(
        self, m_should_reboot, m_load_file
    ):
        m_load_file.side_effect = FileNotFoundError()
        assert get_reboot_status() == RebootStatus.REBOOT_REQUIRED
        assert 1 == m_should_reboot.call_count
        assert 1 == m_load_file.call_count

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @mock.patch("uaclient.security_status.subp")
    @mock.patch("uaclient.security_status.which", return_value=True)
    @mock.patch("uaclient.security_status.load_file")
    @mock.patch("uaclient.security_status.should_reboot", return_value=True)
    def test_get_reboot_status_fail_to_parse_livepatch_output(
        self,
        m_should_reboot,
        m_load_file,
        _m_which,
        m_subp,
        caplog_text,
    ):
        m_load_file.return_value = "linux-image-5.4.0-1074\nlinux-base"
        m_subp.return_value = ('{"test": 123', "")

        assert get_reboot_status() == RebootStatus.REBOOT_REQUIRED
        assert "Could not parse Livepatch Status JSON" in caplog_text()

    @pytest.mark.parametrize(
        "pkgs,expected_state",
        (
            ("pkg1\npkg2", RebootStatus.REBOOT_REQUIRED),
            (
                "linux-image-5.4.0-1074\nlinux-base\npkg2",
                RebootStatus.REBOOT_REQUIRED,
            ),
        ),
    )
    @mock.patch("uaclient.security_status.load_file")
    @mock.patch("uaclient.security_status.should_reboot", return_value=True)
    def test_get_reboot_status_reboot_pkgs_file_present(
        self, m_should_reboot, m_load_file, pkgs, expected_state
    ):
        m_load_file.return_value = pkgs
        assert get_reboot_status() == expected_state
        assert 1 == m_should_reboot.call_count
        assert 1 == m_load_file.call_count

    @pytest.mark.parametrize(
        "livepatch_state,expected_state,kernel_name",
        (
            (
                "applied",
                RebootStatus.REBOOT_REQUIRED_LIVEPATCH_APPLIED,
                "4.15.0-187.198-generic",
            ),
            ("applied", RebootStatus.REBOOT_REQUIRED, "test"),
            (
                "nothing-to-apply",
                RebootStatus.REBOOT_REQUIRED,
                "4.15.0-187.198-generic",
            ),
            (
                "applying",
                RebootStatus.REBOOT_REQUIRED,
                "4.15.0-187.198-generic",
            ),
            (
                "apply-failed",
                RebootStatus.REBOOT_REQUIRED,
                "4.15.0-187.198-generic",
            ),
        ),
    )
    @mock.patch("uaclient.security_status.get_kernel_info")
    @mock.patch("uaclient.security_status.which")
    @mock.patch("uaclient.security_status.subp")
    @mock.patch("uaclient.security_status.load_file")
    @mock.patch("uaclient.security_status.should_reboot", return_value=True)
    def test_get_reboot_status_reboot_pkgs_file_only_kernel_pkgs(
        self,
        m_should_reboot,
        m_load_file,
        m_subp,
        m_which,
        m_kernel_info,
        livepatch_state,
        expected_state,
        kernel_name,
    ):
        m_kernel_info.return_value = mock.MagicMock(
            proc_version_signature_version=kernel_name
        )
        m_which.return_value = True
        m_load_file.return_value = "linux-image-5.4.0-1074\nlinux-base"
        m_subp.return_value = (
            """
            {{
              "Client-Version": "version",
              "Machine-Id": "machine-id",
              "Architecture": "x86_64",
              "CPU-Model": "Intel(R) Core(TM) i7-8650U CPU @ 1.90GHz",
              "Last-Check": "2022-07-05T18:29:00Z",
              "Boot-Time": "2022-07-05T18:27:12Z",
              "Uptime": "203",
              "Status": [
                {{
                    "Kernel": "4.15.0-187.198-generic",
                    "Running": true,
                    "Livepatch": {{
                        "CheckState": "checked",
                        "State": "{}",
                        "Version": ""
                    }}
                }}
              ],
              "tier": "stable"
            }}
        """.format(
                livepatch_state
            ),
            "",
        )

        assert get_reboot_status() == expected_state
        assert 1 == m_should_reboot.call_count
        assert 1 == m_load_file.call_count
        assert 1 == m_which.call_count
        assert 1 == m_subp.call_count
        assert 1 == m_kernel_info.call_count

    @mock.patch("uaclient.security_status.get_kernel_info")
    @mock.patch("uaclient.security_status.which")
    @mock.patch("uaclient.security_status.subp")
    @mock.patch("uaclient.security_status.load_file")
    @mock.patch("uaclient.security_status.should_reboot", return_value=True)
    def test_get_reboot_status_fail_parsing_kernel_info(
        self,
        m_should_reboot,
        m_load_file,
        m_subp,
        m_which,
        m_kernel_info,
    ):
        m_kernel_info.return_value = mock.MagicMock(
            proc_version_signature_version=None
        )
        m_which.return_value = True
        m_load_file.return_value = "linux-image-5.4.0-1074\nlinux-base"
        m_subp.return_value = (
            """
            {
              "Client-Version": "version",
              "Machine-Id": "machine-id",
              "Architecture": "x86_64",
              "CPU-Model": "Intel(R) Core(TM) i7-8650U CPU @ 1.90GHz",
              "Last-Check": "2022-07-05T18:29:00Z",
              "Boot-Time": "2022-07-05T18:27:12Z",
              "Uptime": "203",
              "Status": [
                {
                    "Kernel": "4.15.0-187.198-generic",
                    "Running": true,
                    "Livepatch": {
                        "CheckState": "checked",
                        "State": "applied",
                        "Version": ""
                    }
                }
              ],
              "tier": "stable"
            }
            """,
            "",
        )

        assert get_reboot_status() == RebootStatus.REBOOT_REQUIRED
        assert 1 == m_should_reboot.call_count
        assert 1 == m_load_file.call_count
        assert 1 == m_which.call_count
        assert 1 == m_subp.call_count
        assert 1 == m_kernel_info.call_count
