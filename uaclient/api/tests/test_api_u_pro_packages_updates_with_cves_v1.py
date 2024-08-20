import datetime

import mock

from uaclient.api.u.pro.packages.updates.v1 import (
    PackageUpdatesResult,
    UpdateInfo,
    UpdateSummary,
)
from uaclient.api.u.pro.packages.updates_with_cves.v1 import (
    CVEInfo,
    PackageUpdatesWithCVEsResult,
    UpdateInfoWithCVES,
    _updates_with_cves,
)

PACKAGE_UPDATES = PackageUpdatesResult(
    summary=UpdateSummary(
        num_updates=3,
        num_esm_apps_updates=1,
        num_esm_infra_updates=1,
        num_standard_security_updates=1,
        num_standard_updates=0,
    ),
    updates=[
        UpdateInfo(
            download_size=100,
            origin="esm.ubuntu.com",
            package="pkg1",
            provided_by="esm-infra",
            status="pending_attach",
            version="1.2",
        ),
        UpdateInfo(
            download_size=100,
            origin="esm.ubuntu.com",
            package="pkg2",
            provided_by="esm-apps",
            status="pending_attach",
            version="1.1",
        ),
        UpdateInfo(
            download_size=100,
            origin="archive.ubuntu.com",
            package="pkg3",
            provided_by="standard-updates",
            status="upgrade_available",
            version="1.3",
        ),
    ],
)

VULNERABILITIES_DATA = {
    "published_at": "2024-06-24T13:19:16",
    "packages": {
        "pkg1": {
            "source_versions": {
                "1.2": {
                    "binary_packages": {
                        "pkg1": "1.2",
                    },
                    "pocket": "esm-infra",
                }
            },
            "cves": {
                "CVE-2022-7896": {
                    "source_fixed_version": None,
                    "status": "vulnerable",
                },
                "CVE-2022-12345": {
                    "source_fixed_version": "1.2",
                    "status": "vulnerable",
                },
            },
        },
        "pkg2": {
            "source_versions": {
                "1.1": {
                    "binary_packages": {
                        "pkg2": "1.1",
                    },
                    "pocket": "esm-apps",
                }
            },
            "cves": {
                "CVE-2022-56789": {
                    "source_fixed_version": "1.1",
                    "status": "fixed",
                },
                "CVE-2022-18976": {
                    "source_fixed_version": "1.0.9",
                    "status": "vulnerable",
                },
            },
        },
    },
    "security_issues": {
        "cves": {
            "CVE-2022-12345": {
                "description": "description",
                "published_at": "2024-06-24T13:19:16",
                "notes": ["hint"],
                "ubuntu_priority": "low",
                "mitigation": "hint",
                "cvss_severity": "low",
                "cvss_score": 4.2,
            },
            "CVE-2022-56789": {
                "description": "description",
                "published_at": "2024-06-24T13:19:16",
                "notes": ["hint"],
                "mitigation": "hint",
                "ubuntu_priority": "low",
                "cvss_severity": "low",
                "cvss_score": 4.2,
            },
        }
    },
}


class TestPackagesWithCVEs:
    M_PATH = "uaclient.api.u.pro.packages.updates_with_cves.v1."

    @mock.patch(M_PATH + "VulnerabilityData.get")
    @mock.patch(M_PATH + "_get_pkg_current_version")
    @mock.patch(M_PATH + "_get_pkg_updates")
    def test_packages_with_cves(
        self,
        m_get_pkg_updates,
        m_get_pkg_curr_version,
        m_vulnerability_data_get,
    ):
        m_vulnerability_data_get.return_value = VULNERABILITIES_DATA
        m_get_pkg_updates.return_value = PACKAGE_UPDATES
        m_get_pkg_curr_version.side_effect = ["1.1", "1.0.12", "1.3"]

        assert _updates_with_cves(
            options=mock.MagicMock(data_file=None), cfg=None
        ) == PackageUpdatesWithCVEsResult(
            summary=UpdateSummary(
                num_updates=3,
                num_esm_apps_updates=1,
                num_esm_infra_updates=1,
                num_standard_security_updates=1,
                num_standard_updates=0,
            ),
            updates=[
                UpdateInfoWithCVES(
                    download_size=100,
                    origin="esm.ubuntu.com",
                    package="pkg1",
                    provided_by="esm-infra",
                    status="pending_attach",
                    version="1.2",
                    related_cves=["CVE-2022-12345"],
                ),
                UpdateInfoWithCVES(
                    download_size=100,
                    origin="esm.ubuntu.com",
                    package="pkg2",
                    provided_by="esm-apps",
                    status="pending_attach",
                    version="1.1",
                    related_cves=["CVE-2022-56789"],
                ),
                UpdateInfoWithCVES(
                    download_size=100,
                    origin="archive.ubuntu.com",
                    package="pkg3",
                    provided_by="standard-updates",
                    status="upgrade_available",
                    version="1.3",
                    related_cves=[],
                ),
            ],
            cves=[
                CVEInfo(
                    name="CVE-2022-12345",
                    description="description",
                    published_at=datetime.datetime(2024, 6, 24, 13, 19, 16),
                    ubuntu_priority="low",
                    notes=["hint"],
                    cvss_severity="low",
                    cvss_score=4.2,
                ),
                CVEInfo(
                    name="CVE-2022-56789",
                    description="description",
                    published_at=datetime.datetime(2024, 6, 24, 13, 19, 16),
                    ubuntu_priority="low",
                    notes=["hint"],
                    cvss_severity="low",
                    cvss_score=4.2,
                ),
            ],
            vulnerability_data_published_at=datetime.datetime(
                2024, 6, 24, 13, 19, 16
            ),
        )
