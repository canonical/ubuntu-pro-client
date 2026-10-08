import copy
import datetime

import mock
import pytest

from uaclient.api.u.pro.security.usns.v1 import (
    AffectedPackage,
    USNAffectedPackage,
    USNInfo,
    USNsOptions,
    USNsResult,
    _usns,
)

M_PATH = "uaclient.api.u.pro.security.usns.v1."
M_VULN_COMMON_PATH = "uaclient.api.u.pro.security.cves._common.v1."

VULNERABILITIES_DATA = {
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
                },
                "1.1.3": {
                    "binary_packages": {
                        "test1-bin": "1.1.3",
                        "test1-bin1": "1.1.3",
                    },
                    "pocket": "esm-infra",
                },
            },
            "ubuntu_security_notices": {
                "USN-1234-1": {"source_fixed_version": "1.1.2"},
                "USN-1234-2": {"source_fixed_version": "1.1.3"},
            },
            "ubuntu_security_notices_regressions": {},
            "cves": {},
        }
    },
    "security_issues": {
        "cves": {
            "CVE-2022-0001": {"ubuntu_priority": "high"},
            "CVE-2022-0002": {"ubuntu_priority": "low"},
        },
        "usns": {
            "USN-1234-1": {
                "title": "Test USN",
                "description": "description",
                "published_at": "2024-06-24T13:19:16",
                "related_cves": ["CVE-2022-0001", "CVE-2022-0002"],
                "related_launchpad_bugs": [],
            },
            "USN-1234-2": {
                "title": "Test USN regression",
                "description": "description2",
                "published_at": "2024-07-01T13:19:16",
                "related_cves": ["CVE-2022-0002"],
                "related_launchpad_bugs": [],
            },
        },
    },
}


INSTALLED_PKGS_BY_SOURCE = {
    "test1": {
        "test1-bin": "1.1.1",
        "test1-bin1": "1.1.1",
    }
}


def _expected_packages():
    usns = [
        USNAffectedPackage(
            name="USN-1234-1",
            fix_version="1.1.2",
            fix_status="fixed",
            fix_origin="esm-infra",
        ),
        USNAffectedPackage(
            name="USN-1234-2",
            fix_version="1.1.3",
            fix_status="fixed",
            fix_origin="esm-infra",
        ),
    ]
    return {
        "test1-bin": AffectedPackage(current_version="1.1.1", usns=list(usns)),
        "test1-bin1": AffectedPackage(
            current_version="1.1.1", usns=list(usns)
        ),
    }


class TestUSNs:
    @pytest.mark.parametrize(
        "vulnerabilities_data,installed_pkgs_by_source,usn_options,expected_result",  # noqa
        (
            (
                VULNERABILITIES_DATA,
                INSTALLED_PKGS_BY_SOURCE,
                USNsOptions(),
                USNsResult(
                    packages=_expected_packages(),
                    usns={
                        "USN-1234-1": USNInfo(
                            title="Test USN",
                            description="description",
                            published_at=datetime.datetime(
                                2024,
                                6,
                                24,
                                13,
                                19,
                                16,
                                tzinfo=datetime.timezone.utc,
                            ),
                            # updated_at is the published date of the latest
                            # revision in the family (USN-1234-2)
                            updated_at=datetime.datetime(
                                2024,
                                7,
                                1,
                                13,
                                19,
                                16,
                                tzinfo=datetime.timezone.utc,
                            ),
                            revision=1,
                            superseded_by="USN-1234-2",
                            # derived from the most severe related CVE priority
                            priority="high",
                            notes=[],
                            related_cves=[
                                "CVE-2022-0001",
                                "CVE-2022-0002",
                            ],
                            affected_packages=["test1-bin", "test1-bin1"],
                        ),
                        "USN-1234-2": USNInfo(
                            title="Test USN regression",
                            description="description2",
                            published_at=datetime.datetime(
                                2024,
                                7,
                                1,
                                13,
                                19,
                                16,
                                tzinfo=datetime.timezone.utc,
                            ),
                            updated_at=None,
                            revision=2,
                            superseded_by=None,
                            priority="low",
                            notes=[],
                            related_cves=["CVE-2022-0002"],
                            affected_packages=["test1-bin", "test1-bin1"],
                        ),
                    },
                    vulnerability_data_published_at=datetime.datetime(
                        2024, 6, 24, 13, 19, 16, tzinfo=datetime.timezone.utc
                    ),
                    apt_updated_at=datetime.datetime(2024, 6, 24, 13, 19, 16),
                ),
            ),
            # All applicable USNs are fixable, so fixable == default
            (
                VULNERABILITIES_DATA,
                INSTALLED_PKGS_BY_SOURCE,
                USNsOptions(unfixable=True),
                USNsResult(
                    packages={},
                    usns={},
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
    @mock.patch(
        M_VULN_COMMON_PATH + "VulnerabilityData.refreshed",
        new_callable=mock.PropertyMock,
    )
    @mock.patch(M_VULN_COMMON_PATH + "query_installed_source_pkg_versions")
    def test_parse_data(
        self,
        m_get_source_pkgs,
        _m_vulnerability_data_refreshed,
        m_vulnerability_data_get,
        m_get_apt_cache_datetime,
        _m_vulnerability_result_save_cache,
        vulnerabilities_data,
        installed_pkgs_by_source,
        usn_options,
        expected_result,
    ):
        m_get_source_pkgs.return_value = installed_pkgs_by_source
        m_vulnerability_data_get.return_value = copy.deepcopy(
            vulnerabilities_data
        )
        m_get_apt_cache_datetime.return_value = datetime.datetime(
            2024, 6, 24, 13, 19, 16
        )
        assert _usns(usn_options, None) == expected_result
