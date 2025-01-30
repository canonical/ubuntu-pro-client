import mock
import pytest

from uaclient.api.u.pro.security.vulnerabilities._common.v1 import (
    VulnerabilitiesAlreadyFixed,
    VulnerabilityParser,
    VulnerabilityStatus,
    _get_vulnerability_fix_status,
)

M_PATH = "uaclient.api.u.pro.security.vulnerabilities._common.v1."


VULNERABILITIES_DATA = {
    "packages": {
        "test1": {
            "source_versions": {
                "1.1.2": {
                    "binary_packages": {
                        "test1-bin": "1.1.5",
                        "test1-bin1": "1.1.2",
                    },
                    "pocket": "esm-infra",
                },
                "1.1.3": {
                    "binary_packages": {
                        "test1-bin": "1.1.5",
                        "test1-bin1": "1.1.2",
                        "test1-bin2": "1.1.3",
                    },
                    "pocket": "esm-infra",
                },
                "1.1.4": {
                    "binary_packages": {
                        "test1-bin1": "1.1.5",
                    },
                    "pocket": "esm-infra",
                },
            },
            "cves": {
                "CVE-2022-12345": {
                    "source_fixed_version": None,
                    "status": "vulnerable",
                },
                "CVE-2022-56789": {
                    "source_fixed_version": "1.1.2",
                    "status": "fixed",
                },
                "CVE-2022-18976": {
                    "source_fixed_version": "1.0.9",
                    "status": "vulnerable",
                },
                "CVE-2022-95632": {
                    "source_fixed_version": None,
                    "status": "not-vulnerable",
                },
                "CVE-2022-86782": {
                    "source_fixed_version": "1.1.4",
                    "status": "fixed",
                },
            },
        },
        "test2": {
            "source_versions": {
                "1.1.2": {
                    "binary_packages": {
                        "test2-bin2-1": "1.1.2",
                    },
                    "pocket": "esm-infra",
                }
            },
            "cves": {
                "CVE-2022-12345": {
                    "source_fixed_version": None,
                    "status": "vulnerable",
                },
            },
        },
    },
    "security_issues": {
        "cves": {
            "CVE-2022-12345": {
                "description": "description",
                "published_at": "date",
                "notes": ["hint"],
                "mitigation": "hint",
                "cvss_severity": "low",
                "cvss_score": 4.2,
            },
            "CVE-2022-56789": {
                "description": "description",
                "published_at": "date",
                "notes": ["hint"],
                "mitigation": "hint",
                "cvss_severity": "low",
                "cvss_score": 4.2,
            },
            "CVE-2022-86782": {
                "description": "description",
                "published_at": "date",
                "notes": ["hint"],
                "mitigation": "hint",
                "cvss_severity": "low",
                "cvss_score": 4.2,
            },
        }
    },
}


class ConcreteVulnerabilityParser(VulnerabilityParser):
    vulnerability_type = "cves"

    def get_package_vulnerabilities(self, affected_pkg):
        return affected_pkg.get(self.vulnerability_type, {})

    def _post_process_vulnerability_info(
        self,
        vulnerability_info,
        vulnerabilities_data,
    ):
        return vulnerability_info


class TestVulnerabilityParser:

    @pytest.mark.parametrize(
        "vulnerabilities_data,installed_pkgs_by_source,expected_result",
        (
            (
                VULNERABILITIES_DATA,
                {
                    "test1": {
                        "test1-bin1": "1.1.1",
                        "test1-bin": "1.1.4",
                    }
                },
                {
                    "packages": {
                        "test1-bin1": {
                            "current_version": "1.1.1",
                            "cves": [
                                {
                                    "name": "CVE-2022-12345",
                                    "fix_version": None,
                                    "fix_status": "vulnerable",
                                    "fix_origin": None,
                                },
                                {
                                    "name": "CVE-2022-56789",
                                    "fix_version": "1.1.2",
                                    "fix_status": "fixed",
                                    "fix_origin": "esm-infra",
                                },
                                {
                                    "name": "CVE-2022-86782",
                                    "fix_version": "1.1.5",
                                    "fix_status": "fixed",
                                    "fix_origin": "esm-infra",
                                },
                            ],
                        },
                        "test1-bin": {
                            "current_version": "1.1.4",
                            "cves": [
                                {
                                    "name": "CVE-2022-12345",
                                    "fix_version": None,
                                    "fix_status": "vulnerable",
                                    "fix_origin": None,
                                },
                                {
                                    "name": "CVE-2022-56789",
                                    "fix_version": "1.1.5",
                                    "fix_status": "fixed",
                                    "fix_origin": "esm-infra",
                                },
                                {
                                    "name": "CVE-2022-86782",
                                    "fix_version": None,
                                    "fix_status": "unknown",
                                    "fix_origin": None,
                                },
                            ],
                        },
                    },
                    "vulnerabilities": {
                        "CVE-2022-12345": {
                            "description": "description",
                            "published_at": "date",
                            "notes": ["hint"],
                            "mitigation": "hint",
                            "cvss_severity": "low",
                            "cvss_score": 4.2,
                        },
                        "CVE-2022-56789": {
                            "description": "description",
                            "published_at": "date",
                            "notes": ["hint"],
                            "mitigation": "hint",
                            "cvss_severity": "low",
                            "cvss_score": 4.2,
                        },
                        "CVE-2022-86782": {
                            "description": "description",
                            "published_at": "date",
                            "notes": ["hint"],
                            "mitigation": "hint",
                            "cvss_severity": "low",
                            "cvss_score": 4.2,
                        },
                    },
                },
            ),
        ),
    )
    @mock.patch(
        M_PATH + "VulnerabilityParser._get_installed_source_pkg_version"
    )
    def test_get_vulnerabilities_for_installed_pkgs(
        self,
        m_get_installed_source_pkg_version,
        vulnerabilities_data,
        installed_pkgs_by_source,
        expected_result,
    ):
        m_get_installed_source_pkg_version.return_value = "1.1.3"
        parser = ConcreteVulnerabilityParser()
        assert (
            parser.get_vulnerabilities_for_installed_pkgs(
                vulnerabilities_data, installed_pkgs_by_source
            ).vulnerabilities_info
            == expected_result
        )


class TestGetVulnerabilityFixStatus:
    @pytest.mark.parametrize(
        "affected_pkgs,expected_state",
        (
            (
                [
                    {
                        "fix_version": "1.0",
                        "name": "pkg1",
                    },
                    {
                        "fix_version": "1.0",
                        "name": "pkg2",
                    },
                ],
                VulnerabilityStatus.FULL_FIX_AVAILABLE,
            ),
            (
                [
                    {
                        "fix_version": None,
                        "name": "pkg1",
                    },
                    {
                        "fix_version": "1.0",
                        "name": "pkg2",
                    },
                ],
                VulnerabilityStatus.PARTIAL_FIX_AVAILABLE,
            ),
            (
                [
                    {
                        "fix_version": None,
                        "name": "pkg1",
                    },
                    {
                        "fix_version": None,
                        "name": "pkg2",
                    },
                ],
                VulnerabilityStatus.NO_FIX_AVAILABLE,
            ),
        ),
    )
    def test_get_vulnerability_fix_status(
        self,
        affected_pkgs,
        expected_state,
    ):
        assert _get_vulnerability_fix_status(affected_pkgs) == expected_state


class TestVulnerabilitiesAlreadyFixed:

    @pytest.mark.parametrize(
        "vulnerabilities,expected_result",
        (
            (
                [
                    ("CVE-1234-5", "ubuntu_pro", "high"),
                    ("CVE-1234-5", "ubuntu_pro", "high"),
                    ("CVE-1234-5", "ubuntu_security", "high"),
                    ("CVE-1234-5", "ubuntu_security", "high"),
                    ("CVE-1552-5", "ubuntu_pro", "medium"),
                    ("CVE-1382-5", "ubuntu_security", "low"),
                ],
                {
                    "count": {
                        "ubuntu_pro": 2,
                        "ubuntu_security": 2,
                    },
                    "info": {
                        "ubuntu_pro": {"high": 1, "medium": 1},
                        "ubuntu_security": {"high": 1, "low": 1},
                    },
                },
            ),
            (
                [
                    ("USN-1234-5", "ubuntu_pro"),
                    ("USN-1234-5", "ubuntu_security"),
                    ("USN-1552-5", "ubuntu_pro"),
                    ("USN-1382-5", "ubuntu_security"),
                ],
                {
                    "count": {
                        "ubuntu_pro": 2,
                        "ubuntu_security": 2,
                    },
                    "info": {
                        "ubuntu_pro": {},
                        "ubuntu_security": {},
                    },
                },
            ),
        ),
    )
    def test_vulnerabilities_already_fixed_to_dict(
        self,
        vulnerabilities,
        expected_result,
    ):
        vulnerabilities_already_fixed = VulnerabilitiesAlreadyFixed()
        for vulnerability in vulnerabilities:
            vulnerabilities_already_fixed.add_vulnerability(*vulnerability)

        assert expected_result == vulnerabilities_already_fixed.to_dict()
