import datetime

import mock
import pytest

from uaclient.api.u.pro.security.vulnerabilities.cve.v1 import (
    CVEAffectedPackage,
    CVEVulnerabilitiesOptions,
    CVEVulnerabilitiesResult,
    CVEVulnerabilityResult,
    _vulnerabilities,
)

M_PATH = "uaclient.api.u.pro.security.vulnerabilities.cve.v1."

VULNEBILITIES_DATA = {
    "published_at": "2024-06-24T13:19:16",
    "packages": {
        "test1": {
            "source_versions": {
                "1.1.2": {
                    "binary_packages": {
                        "test1-bin": "1.1.2",
                        "test1-bin1": "1.1.2",
                    },
                    "pocket": "esm-infra",
                }
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
            },
        }
    },
    "security_issues": {
        "cves": {
            "CVE-2022-12345": {
                "description": "description",
                "published_at": "2024-06-24T13:19:16",
                "ubuntu_priority": "low",
                "notes": ["hint"],
                "mitigation": "hint",
                "cvss_severity": "low",
                "cvss_score": 4.2,
            },
            "CVE-2022-56789": {
                "description": "description",
                "published_at": "2024-06-24T13:19:16",
                "ubuntu_priority": "low",
                "notes": ["hint"],
                "mitigation": "hint",
                "cvss_severity": "low",
                "cvss_score": 4.2,
            },
        }
    },
}


INSTALLED_PKGS_BY_SOURCE = {
    "test1": {
        "test1-bin1": "1.1.1",
        "test1-bin": "1.1.1",
    }
}


class TestCVEVulnerabilities:
    @pytest.mark.parametrize(
        "vulnerabilities_data,installed_pkgs_by_source,cve_options,expected_result",  # noqa
        (
            (
                VULNEBILITIES_DATA,
                INSTALLED_PKGS_BY_SOURCE,
                CVEVulnerabilitiesOptions(all=True),
                CVEVulnerabilitiesResult(
                    cves=[
                        CVEVulnerabilityResult(
                            name="CVE-2022-12345",
                            description="description",
                            ubuntu_priority="low",
                            fixable="no",
                            affected_packages=[
                                CVEAffectedPackage(
                                    name="test1-bin",
                                    current_version="1.1.1",
                                    fix_version=None,
                                    fix_status="vulnerable",
                                    fix_available_from=None,
                                ),
                                CVEAffectedPackage(
                                    name="test1-bin1",
                                    current_version="1.1.1",
                                    fix_version=None,
                                    fix_status="vulnerable",
                                    fix_available_from=None,
                                ),
                            ],
                            published_at=datetime.datetime(
                                2024,
                                6,
                                24,
                                13,
                                19,
                                16,
                                tzinfo=datetime.timezone.utc,
                            ),
                            notes=["hint"],
                            cvss_severity="low",
                            cvss_score=4.2,
                        ),
                        CVEVulnerabilityResult(
                            name="CVE-2022-56789",
                            description="description",
                            ubuntu_priority="low",
                            fixable="yes",
                            affected_packages=[
                                CVEAffectedPackage(
                                    name="test1-bin",
                                    current_version="1.1.1",
                                    fix_version="1.1.2",
                                    fix_status="fixed",
                                    fix_available_from="esm-infra",
                                ),
                                CVEAffectedPackage(
                                    name="test1-bin1",
                                    current_version="1.1.1",
                                    fix_version="1.1.2",
                                    fix_status="fixed",
                                    fix_available_from="esm-infra",
                                ),
                            ],
                            published_at=datetime.datetime(
                                2024,
                                6,
                                24,
                                13,
                                19,
                                16,
                                tzinfo=datetime.timezone.utc,
                            ),
                            notes=["hint"],
                            cvss_severity="low",
                            cvss_score=4.2,
                        ),
                    ],
                    vulnerability_data_published_at=datetime.datetime(
                        2024, 6, 24, 13, 19, 16, tzinfo=datetime.timezone.utc
                    ),
                    apt_updated_at=datetime.datetime(2024, 6, 24, 13, 19, 16),
                ),
            ),
            (
                VULNEBILITIES_DATA,
                INSTALLED_PKGS_BY_SOURCE,
                CVEVulnerabilitiesOptions(),
                CVEVulnerabilitiesResult(
                    cves=[
                        CVEVulnerabilityResult(
                            name="CVE-2022-56789",
                            description="description",
                            ubuntu_priority="low",
                            fixable="yes",
                            affected_packages=[
                                CVEAffectedPackage(
                                    name="test1-bin",
                                    current_version="1.1.1",
                                    fix_version="1.1.2",
                                    fix_status="fixed",
                                    fix_available_from="esm-infra",
                                ),
                                CVEAffectedPackage(
                                    name="test1-bin1",
                                    current_version="1.1.1",
                                    fix_version="1.1.2",
                                    fix_status="fixed",
                                    fix_available_from="esm-infra",
                                ),
                            ],
                            published_at=datetime.datetime(
                                2024,
                                6,
                                24,
                                13,
                                19,
                                16,
                                tzinfo=datetime.timezone.utc,
                            ),
                            notes=["hint"],
                            cvss_severity="low",
                            cvss_score=4.2,
                        ),
                    ],
                    vulnerability_data_published_at=datetime.datetime(
                        2024, 6, 24, 13, 19, 16, tzinfo=datetime.timezone.utc
                    ),
                    apt_updated_at=datetime.datetime(2024, 6, 24, 13, 19, 16),
                ),
            ),
            (
                VULNEBILITIES_DATA,
                INSTALLED_PKGS_BY_SOURCE,
                CVEVulnerabilitiesOptions(unfixable=True),
                CVEVulnerabilitiesResult(
                    cves=[
                        CVEVulnerabilityResult(
                            name="CVE-2022-12345",
                            description="description",
                            ubuntu_priority="low",
                            fixable="no",
                            affected_packages=[
                                CVEAffectedPackage(
                                    name="test1-bin",
                                    current_version="1.1.1",
                                    fix_version=None,
                                    fix_status="vulnerable",
                                    fix_available_from=None,
                                ),
                                CVEAffectedPackage(
                                    name="test1-bin1",
                                    current_version="1.1.1",
                                    fix_version=None,
                                    fix_status="vulnerable",
                                    fix_available_from=None,
                                ),
                            ],
                            published_at=datetime.datetime(
                                2024,
                                6,
                                24,
                                13,
                                19,
                                16,
                                tzinfo=datetime.timezone.utc,
                            ),
                            notes=["hint"],
                            cvss_severity="low",
                            cvss_score=4.2,
                        ),
                    ],
                    vulnerability_data_published_at=datetime.datetime(
                        2024, 6, 24, 13, 19, 16, tzinfo=datetime.timezone.utc
                    ),
                    apt_updated_at=datetime.datetime(2024, 6, 24, 13, 19, 16),
                ),
            ),
        ),
    )
    @mock.patch(M_PATH + "get_apt_cache_datetime")
    @mock.patch(M_PATH + "VulnerabilityData.get")
    @mock.patch(M_PATH + "SourcePackages.get")
    def test_parse_data(
        self,
        m_get_source_pkgs,
        m_vulnerability_data_get,
        m_get_apt_cache_datetime,
        vulnerabilities_data,
        installed_pkgs_by_source,
        cve_options,
        expected_result,
    ):
        m_get_source_pkgs.return_value = installed_pkgs_by_source
        m_vulnerability_data_get.return_value = vulnerabilities_data
        m_get_apt_cache_datetime.return_value = datetime.datetime(
            2024, 6, 24, 13, 19, 16
        )
        assert _vulnerabilities(cve_options, None) == expected_result
