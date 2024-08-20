import datetime

import mock
import pytest

from uaclient.api.u.pro.security.vulnerabilities.usn.v1 import (
    USNAffectedPackage,
    USNVulnerabilitiesOptions,
    USNVulnerabilitiesResult,
    USNVulnerabilityResult,
    _vulnerabilities,
)

M_PATH = "uaclient.api.u.pro.security.vulnerabilities.usn.v1."

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
            "ubuntu_security_notices_regressions": {
                "USN-2022-1": {
                    "source_fixed_version": None,
                },
            },
            "ubuntu_security_notices": {
                "USN-2022-5": {
                    "source_fixed_version": "1.1.2",
                },
                "USN-2022-18": {
                    "source_fixed_version": "1.0.9",
                },
                "USN-2022-9": {
                    "source_fixed_version": None,
                },
            },
        }
    },
    "security_issues": {
        "usns": {
            "USN-2022-1": {
                "description": "description",
                "published_at": "2024-06-24T13:19:16",
                "related_cves": [],
                "related_launchpad_bugs": [
                    "https://launchpad.net/bugs/BUG_ID"
                ],
            },
            "USN-2022-5": {
                "description": "description",
                "published_at": "2024-06-24T13:19:16",
                "related_cves": ["CVE-2022-12345"],
                "related_launchpad_bugs": [],
            },
            "USN-2022-9": {
                "description": "description",
                "published_at": "2024-06-24T13:19:16",
                "related_cves": ["CVE-2022-12345"],
                "related_launchpad_bugs": [],
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


class TestUSNVulnerabilities:
    @pytest.mark.parametrize(
        "vulnerabilities_data,installed_pkgs_by_source,usn_options,expected_result",  # noqa
        (
            (
                VULNEBILITIES_DATA,
                INSTALLED_PKGS_BY_SOURCE,
                USNVulnerabilitiesOptions(all=True),
                USNVulnerabilitiesResult(
                    usns=[
                        USNVulnerabilityResult(
                            name="USN-2022-1",
                            description="description",
                            fixable="no",
                            affected_packages=[
                                USNAffectedPackage(
                                    name="test1-bin",
                                    current_version="1.1.1",
                                    fix_version=None,
                                    fix_available_from=None,
                                ),
                                USNAffectedPackage(
                                    name="test1-bin1",
                                    current_version="1.1.1",
                                    fix_version=None,
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
                            related_cves=[],
                            related_launchpad_bugs=[
                                "https://launchpad.net/bugs/BUG_ID"
                            ],
                        ),
                        USNVulnerabilityResult(
                            name="USN-2022-5",
                            description="description",
                            fixable="yes",
                            affected_packages=[
                                USNAffectedPackage(
                                    name="test1-bin",
                                    current_version="1.1.1",
                                    fix_version="1.1.2",
                                    fix_available_from="esm-infra",
                                ),
                                USNAffectedPackage(
                                    name="test1-bin1",
                                    current_version="1.1.1",
                                    fix_version="1.1.2",
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
                            related_cves=["CVE-2022-12345"],
                            related_launchpad_bugs=[],
                        ),
                        USNVulnerabilityResult(
                            name="USN-2022-9",
                            description="description",
                            fixable="no",
                            affected_packages=[
                                USNAffectedPackage(
                                    name="test1-bin",
                                    current_version="1.1.1",
                                    fix_version=None,
                                    fix_available_from=None,
                                ),
                                USNAffectedPackage(
                                    name="test1-bin1",
                                    current_version="1.1.1",
                                    fix_version=None,
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
                            related_cves=["CVE-2022-12345"],
                            related_launchpad_bugs=[],
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
                USNVulnerabilitiesOptions(),
                USNVulnerabilitiesResult(
                    usns=[
                        USNVulnerabilityResult(
                            name="USN-2022-5",
                            description="description",
                            fixable="yes",
                            affected_packages=[
                                USNAffectedPackage(
                                    name="test1-bin",
                                    current_version="1.1.1",
                                    fix_version="1.1.2",
                                    fix_available_from="esm-infra",
                                ),
                                USNAffectedPackage(
                                    name="test1-bin1",
                                    current_version="1.1.1",
                                    fix_version="1.1.2",
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
                            related_cves=["CVE-2022-12345"],
                            related_launchpad_bugs=[],
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
                USNVulnerabilitiesOptions(unfixable=True),
                USNVulnerabilitiesResult(
                    usns=[
                        USNVulnerabilityResult(
                            name="USN-2022-1",
                            description="description",
                            fixable="no",
                            affected_packages=[
                                USNAffectedPackage(
                                    name="test1-bin",
                                    current_version="1.1.1",
                                    fix_version=None,
                                    fix_available_from=None,
                                ),
                                USNAffectedPackage(
                                    name="test1-bin1",
                                    current_version="1.1.1",
                                    fix_version=None,
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
                            related_cves=[],
                            related_launchpad_bugs=[
                                "https://launchpad.net/bugs/BUG_ID"
                            ],
                        ),
                        USNVulnerabilityResult(
                            name="USN-2022-9",
                            description="description",
                            fixable="no",
                            affected_packages=[
                                USNAffectedPackage(
                                    name="test1-bin",
                                    current_version="1.1.1",
                                    fix_version=None,
                                    fix_available_from=None,
                                ),
                                USNAffectedPackage(
                                    name="test1-bin1",
                                    current_version="1.1.1",
                                    fix_version=None,
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
                            related_cves=["CVE-2022-12345"],
                            related_launchpad_bugs=[],
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
        usn_options,
        expected_result,
    ):
        m_get_source_pkgs.return_value = installed_pkgs_by_source
        m_vulnerability_data_get.return_value = vulnerabilities_data
        m_get_apt_cache_datetime.return_value = datetime.datetime(
            2024, 6, 24, 13, 19, 16
        )
        assert _vulnerabilities(usn_options, None) == expected_result
