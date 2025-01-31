import copy
import datetime

import mock
import pytest

from uaclient.api.u.pro.security.vulnerabilities.cve.v1 import (
    AffectedPackage,
    CVEAffectedPackage,
    CVEInfo,
    CVEVulnerabilitiesOptions,
    PackageVulnerabilitiesResult,
    RelatedUSN,
    _vulnerabilities,
)

M_PATH = "uaclient.api.u.pro.security.vulnerabilities.cve.v1."
M_VULN_COMMON_PATH = "uaclient.api.u.pro.security.vulnerabilities._common.v1."

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
                "related_usns": ["USN-1582-1"],
                "related_packages": ["test1-bin", "test1-bin1"],
            },
            "CVE-2022-56789": {
                "description": "description",
                "published_at": "2024-06-24T13:19:16",
                "ubuntu_priority": "low",
                "notes": ["hint"],
                "mitigation": "hint",
                "cvss_severity": "low",
                "cvss_score": 4.2,
                "related_usns": [],
            },
        },
        "usns": {
            "USN-1582-1": {
                "title": "USN Title",
                "description": "description",
            },
        },
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
                CVEVulnerabilitiesOptions(),
                PackageVulnerabilitiesResult(
                    packages={
                        "test1-bin": AffectedPackage(
                            current_version="1.1.1",
                            cves=[
                                CVEAffectedPackage(
                                    name="CVE-2022-12345",
                                    fix_version=None,
                                    fix_status="vulnerable",
                                    fix_origin=None,
                                ),
                                CVEAffectedPackage(
                                    name="CVE-2022-56789",
                                    fix_version="1.1.2",
                                    fix_status="fixed",
                                    fix_origin="esm-infra",
                                ),
                            ],
                        ),
                        "test1-bin1": AffectedPackage(
                            current_version="1.1.1",
                            cves=[
                                CVEAffectedPackage(
                                    name="CVE-2022-12345",
                                    fix_version=None,
                                    fix_status="vulnerable",
                                    fix_origin=None,
                                ),
                                CVEAffectedPackage(
                                    name="CVE-2022-56789",
                                    fix_version="1.1.2",
                                    fix_status="fixed",
                                    fix_origin="esm-infra",
                                ),
                            ],
                        ),
                    },
                    cves={
                        "CVE-2022-12345": CVEInfo(
                            description="description",
                            priority="low",
                            notes=["hint"],
                            published_at=datetime.datetime(
                                2024,
                                6,
                                24,
                                13,
                                19,
                                16,
                                tzinfo=datetime.timezone.utc,
                            ),
                            cvss_severity="low",
                            cvss_score=4.2,
                            related_usns=[
                                RelatedUSN(
                                    name="USN-1582-1",
                                    title="USN Title",
                                )
                            ],
                            related_packages=["test1-bin", "test1-bin1"],
                        ),
                        "CVE-2022-56789": CVEInfo(
                            description="description",
                            priority="low",
                            notes=["hint"],
                            published_at=datetime.datetime(
                                2024,
                                6,
                                24,
                                13,
                                19,
                                16,
                                tzinfo=datetime.timezone.utc,
                            ),
                            cvss_severity="low",
                            cvss_score=4.2,
                            related_usns=[],
                            related_packages=[],
                        ),
                    },
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
                PackageVulnerabilitiesResult(
                    packages={
                        "test1-bin": AffectedPackage(
                            current_version="1.1.1",
                            cves=[
                                CVEAffectedPackage(
                                    name="CVE-2022-12345",
                                    fix_version=None,
                                    fix_status="vulnerable",
                                    fix_origin=None,
                                ),
                            ],
                        ),
                        "test1-bin1": AffectedPackage(
                            current_version="1.1.1",
                            cves=[
                                CVEAffectedPackage(
                                    name="CVE-2022-12345",
                                    fix_version=None,
                                    fix_status="vulnerable",
                                    fix_origin=None,
                                ),
                            ],
                        ),
                    },
                    cves={
                        "CVE-2022-12345": CVEInfo(
                            description="description",
                            priority="low",
                            notes=["hint"],
                            published_at=datetime.datetime(
                                2024,
                                6,
                                24,
                                13,
                                19,
                                16,
                                tzinfo=datetime.timezone.utc,
                            ),
                            cvss_severity="low",
                            cvss_score=4.2,
                            related_usns=[
                                RelatedUSN(
                                    name="USN-1582-1",
                                    title="USN Title",
                                )
                            ],
                            related_packages=["test1-bin", "test1-bin1"],
                        ),
                    },
                    vulnerability_data_published_at=datetime.datetime(
                        2024, 6, 24, 13, 19, 16, tzinfo=datetime.timezone.utc
                    ),
                    apt_updated_at=datetime.datetime(2024, 6, 24, 13, 19, 16),
                ),
            ),
            (
                VULNEBILITIES_DATA,
                INSTALLED_PKGS_BY_SOURCE,
                CVEVulnerabilitiesOptions(fixable=True),
                PackageVulnerabilitiesResult(
                    packages={
                        "test1-bin": AffectedPackage(
                            current_version="1.1.1",
                            cves=[
                                CVEAffectedPackage(
                                    name="CVE-2022-56789",
                                    fix_version="1.1.2",
                                    fix_status="fixed",
                                    fix_origin="esm-infra",
                                ),
                            ],
                        ),
                        "test1-bin1": AffectedPackage(
                            current_version="1.1.1",
                            cves=[
                                CVEAffectedPackage(
                                    name="CVE-2022-56789",
                                    fix_version="1.1.2",
                                    fix_status="fixed",
                                    fix_origin="esm-infra",
                                ),
                            ],
                        ),
                    },
                    cves={
                        "CVE-2022-56789": CVEInfo(
                            description="description",
                            priority="low",
                            notes=["hint"],
                            published_at=datetime.datetime(
                                2024,
                                6,
                                24,
                                13,
                                19,
                                16,
                                tzinfo=datetime.timezone.utc,
                            ),
                            cvss_severity="low",
                            cvss_score=4.2,
                            related_usns=[],
                            related_packages=[],
                        ),
                    },
                    vulnerability_data_published_at=datetime.datetime(
                        2024, 6, 24, 13, 19, 16, tzinfo=datetime.timezone.utc
                    ),
                    apt_updated_at=datetime.datetime(2024, 6, 24, 13, 19, 16),
                ),
            ),
        ),
    )
    @mock.patch(
        M_VULN_COMMON_PATH + "VulnerabilityResultCache.save_result_cache"
    )
    @mock.patch(M_PATH + "get_apt_cache_datetime")
    @mock.patch(M_VULN_COMMON_PATH + "VulnerabilityData.get")
    @mock.patch(M_VULN_COMMON_PATH + "VulnerabilityData.is_cache_valid")
    @mock.patch(M_VULN_COMMON_PATH + "query_installed_source_pkg_versions")
    def test_parse_data(
        self,
        m_get_source_pkgs,
        m_vulnerability_data_is_cache_valid,
        m_vulnerability_data_get,
        m_get_apt_cache_datetime,
        _m_vulnerability_result_save_cache,
        vulnerabilities_data,
        installed_pkgs_by_source,
        cve_options,
        expected_result,
    ):
        m_vulnerability_data_is_cache_valid.return_value = (False, None)
        m_get_source_pkgs.return_value = installed_pkgs_by_source
        m_vulnerability_data_get.return_value = copy.deepcopy(
            vulnerabilities_data
        )
        m_get_apt_cache_datetime.return_value = datetime.datetime(
            2024, 6, 24, 13, 19, 16
        )
        assert _vulnerabilities(cve_options, None) == expected_result
