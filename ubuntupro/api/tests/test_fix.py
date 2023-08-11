import mock
import pytest

from ubuntupro.api.u.pro.security.fix import (
    AptUpgradeData,
    AttachData,
    EnableData,
    FixPlanAptUpgradeStep,
    FixPlanAttachStep,
    FixPlanEnableStep,
    FixPlanError,
    FixPlanNoOpStep,
    FixPlanResult,
    FixPlanUSNResult,
    FixPlanWarningPackageCannotBeInstalled,
    FixPlanWarningSecurityIssueNotFixed,
    NoOpData,
    PackageCannotBeInstalledData,
    SecurityIssueNotFixedData,
    fix_plan_cve,
    fix_plan_usn,
)
from ubuntupro.contract import ContractExpiryStatus
from ubuntupro.messages import INVALID_SECURITY_ISSUE
from ubuntupro.security import CVEPackageStatus, FixStatus


class TestFixPlan:
    @pytest.mark.parametrize(
        "issue_id", (("CVE-sdsa"), ("test"), (""), (None))
    )
    def test_fix_plan_cve_invalid_security_issue(self, issue_id):
        expected_plan = FixPlanResult(
            title=issue_id,
            expected_status="error",
            plan=[],
            warnings=[],
            error=FixPlanError(
                msg=INVALID_SECURITY_ISSUE.format(issue_id=issue_id).msg,
                code=INVALID_SECURITY_ISSUE.name,
            ),
        )
        assert expected_plan == fix_plan_cve(issue_id, cfg=mock.MagicMock())

    @pytest.mark.parametrize(
        "issue_id", (("USN-sadsa"), ("test"), (""), (None))
    )
    def test_fix_plan_usn_invalid_security_issue(self, issue_id):
        expected_plan = FixPlanUSNResult(
            target_usn_plan=FixPlanResult(
                title=issue_id,
                expected_status="error",
                plan=[],
                warnings=[],
                error=FixPlanError(
                    msg=INVALID_SECURITY_ISSUE.format(issue_id=issue_id).msg,
                    code=INVALID_SECURITY_ISSUE.name,
                ),
            ),
            related_usns_plan=[],
        )
        assert expected_plan == fix_plan_usn(issue_id, cfg=mock.MagicMock())

    @mock.patch(
        "ubuntupro.api.u.pro.security.fix._check_cve_fixed_by_livepatch"
    )
    def test_fix_plan_cve_fixed_by_livepatch(
        self,
        m_check_cve_fixed_by_livepatch,
    ):
        m_check_cve_fixed_by_livepatch.return_value = (
            FixStatus.SYSTEM_NON_VULNERABLE,
            None,
        )
        expected_plan = FixPlanResult(
            title="CVE-1234-1235",
            expected_status=str(FixStatus.SYSTEM_NON_VULNERABLE),
            plan=[
                FixPlanNoOpStep(
                    data=NoOpData(
                        status="cve-fixed-by-livepatch",
                    ),
                    order=1,
                )
            ],
            warnings=[],
            error=None,
        )

        assert expected_plan == fix_plan_cve(
            issue_id="cve-1234-1235", cfg=mock.MagicMock()
        )

    @mock.patch("ubuntupro.api.u.pro.security.fix._get_cve_data")
    @mock.patch(
        "ubuntupro.api.u.pro.security.fix.query_installed_source_pkg_versions"
    )
    @mock.patch(
        "ubuntupro.api.u.pro.security.fix._check_cve_fixed_by_livepatch"
    )
    def test_fix_plan_for_no_affected_packages(
        self,
        m_check_cve_fixed_by_livepatch,
        m_query_installed_pkgs,
        m_get_cve_data,
    ):
        m_check_cve_fixed_by_livepatch.return_value = (None, None)
        m_query_installed_pkgs.return_value = {
            "pkg1": {
                "bin1": "1.0",
                "bin2": "1.1",
            }
        }
        m_get_cve_data.return_value = ({}, {})
        expected_plan = FixPlanResult(
            title="CVE-1234-1235",
            expected_status=str(FixStatus.SYSTEM_NOT_AFFECTED),
            plan=[
                FixPlanNoOpStep(
                    data=NoOpData(
                        status="system-not-affected",
                    ),
                    order=1,
                )
            ],
            warnings=[],
            error=None,
        )

        assert expected_plan == fix_plan_cve(
            issue_id="cve-1234-1235", cfg=mock.MagicMock()
        )

    @mock.patch("ubuntupro.apt.get_pkg_candidate_version")
    @mock.patch("ubuntupro.apt.compare_versions")
    @mock.patch("ubuntupro.api.u.pro.security.fix._get_cve_data")
    @mock.patch(
        "ubuntupro.api.u.pro.security.fix.query_installed_source_pkg_versions"
    )
    @mock.patch(
        "ubuntupro.api.u.pro.security.fix._check_cve_fixed_by_livepatch"
    )
    def test_fix_plan_for_cve(
        self,
        m_check_cve_fixed_by_livepatch,
        m_query_installed_pkgs,
        m_get_cve_data,
        m_apt_compare_versions,
        m_get_pkg_candidate_version,
    ):
        m_check_cve_fixed_by_livepatch.return_value = (None, None)
        m_query_installed_pkgs.return_value = {
            "pkg1": {
                "bin1": "1.0",
                "bin2": "1.1",
            }
        }
        m_get_cve_data.return_value = (
            {
                "pkg1": CVEPackageStatus(
                    cve_response={
                        "status": "released",
                        "pocket": "security",
                    }
                ),
            },
            {
                "pkg1": {
                    "source": {
                        "description": "description",
                        "name": "pkg1",
                        "is_source": True,
                        "version": "1.1",
                    },
                    "bin1": {
                        "is_source": False,
                        "name": "bin1",
                        "version": "1.1",
                    },
                    "bin2": {
                        "is_source": False,
                        "name": "bin2",
                        "version": "1.2",
                    },
                }
            },
        )
        m_apt_compare_versions.side_effect = [False, False, True, True]
        m_get_pkg_candidate_version.side_effect = ["1.1", "1.2"]

        expected_plan = FixPlanResult(
            title="CVE-1234-1235",
            expected_status=str(FixStatus.SYSTEM_NON_VULNERABLE),
            plan=[
                FixPlanAptUpgradeStep(
                    data=AptUpgradeData(
                        binary_packages=["bin1", "bin2"],
                        source_packages=["pkg1"],
                    ),
                    order=1,
                )
            ],
            warnings=[],
            error=None,
        )

        assert expected_plan == fix_plan_cve(
            issue_id="cve-1234-1235", cfg=mock.MagicMock()
        )

    @mock.patch("ubuntupro.api.u.pro.security.fix._enabled_services")
    @mock.patch("ubuntupro.api.u.pro.security.fix._is_attached")
    @mock.patch("ubuntupro.api.u.pro.security.fix.get_contract_expiry_status")
    @mock.patch("ubuntupro.apt.get_pkg_candidate_version")
    @mock.patch("ubuntupro.apt.compare_versions")
    @mock.patch("ubuntupro.api.u.pro.security.fix._get_cve_data")
    @mock.patch(
        "ubuntupro.api.u.pro.security.fix.query_installed_source_pkg_versions"
    )
    @mock.patch(
        "ubuntupro.api.u.pro.security.fix._check_cve_fixed_by_livepatch"
    )
    def test_fix_plan_for_cve_that_requires_pro_services(
        self,
        m_check_cve_fixed_by_livepatch,
        m_query_installed_pkgs,
        m_get_cve_data,
        m_apt_compare_versions,
        m_get_pkg_candidate_version,
        m_get_contract_expiry_status,
        m_is_attached,
        m_enabled_services,
    ):
        m_check_cve_fixed_by_livepatch.return_value = (None, None)
        m_query_installed_pkgs.return_value = {
            "pkg1": {
                "bin1": "1.0",
                "bin2": "1.1",
            },
            "pkg2": {
                "bin3": "1.5",
            },
            "pkg3": {
                "bin4": "1.8",
            },
        }
        m_get_cve_data.return_value = (
            {
                "pkg1": CVEPackageStatus(
                    cve_response={
                        "status": "released",
                        "pocket": "security",
                    }
                ),
                "pkg2": CVEPackageStatus(
                    cve_response={
                        "status": "released",
                        "pocket": "esm-infra",
                    }
                ),
                "pkg3": CVEPackageStatus(
                    cve_response={
                        "status": "released",
                        "pocket": "esm-apps",
                    }
                ),
            },
            {
                "pkg1": {
                    "source": {
                        "description": "description",
                        "name": "pkg1",
                        "is_source": True,
                        "version": "1.1",
                    },
                    "bin1": {
                        "is_source": False,
                        "name": "bin1",
                        "version": "1.1",
                    },
                    "bin2": {
                        "is_source": False,
                        "name": "bin2",
                        "version": "1.2",
                    },
                },
                "pkg2": {
                    "source": {
                        "description": "description",
                        "name": "pkg2",
                        "is_source": True,
                        "version": "1.5",
                    },
                    "bin3": {
                        "is_source": False,
                        "name": "bin3",
                        "version": "1.6~esm1",
                    },
                },
                "pkg3": {
                    "source": {
                        "description": "description",
                        "name": "pkg3",
                        "is_source": True,
                        "version": "1.8",
                    },
                    "bin4": {
                        "is_source": False,
                        "name": "bin4",
                        "version": "1.8.1~esm1",
                    },
                },
            },
        )
        m_apt_compare_versions.side_effect = [
            False,
            False,
            False,
            False,
            True,
            True,
            True,
            True,
        ]
        m_get_pkg_candidate_version.side_effect = [
            "1.1",
            "1.2",
            "1.6~esm1",
            "1.8.1~esm1",
        ]
        m_get_contract_expiry_status.return_value = (
            ContractExpiryStatus.ACTIVE,
            None,
        )
        m_is_attached.side_effect = [
            mock.MagicMock(is_attached=False),
            mock.MagicMock(is_attached=True),
        ]
        m_enabled_services.side_effect = [
            mock.MagicMock(enabled_services=None),
            mock.MagicMock(enabled_services=["esm-infra"]),
        ]

        expected_plan = FixPlanResult(
            title="CVE-1234-1235",
            expected_status=str(FixStatus.SYSTEM_NON_VULNERABLE),
            plan=[
                FixPlanAptUpgradeStep(
                    data=AptUpgradeData(
                        binary_packages=["bin1", "bin2"],
                        source_packages=["pkg1"],
                    ),
                    order=1,
                ),
                FixPlanAttachStep(
                    data=AttachData(
                        reason="required-pro-service",
                    ),
                    order=2,
                ),
                FixPlanEnableStep(
                    data=EnableData(
                        service="esm-infra",
                    ),
                    order=3,
                ),
                FixPlanAptUpgradeStep(
                    data=AptUpgradeData(
                        binary_packages=["bin3"],
                        source_packages=["pkg2"],
                    ),
                    order=4,
                ),
                FixPlanEnableStep(
                    data=EnableData(
                        service="esm-apps",
                    ),
                    order=5,
                ),
                FixPlanAptUpgradeStep(
                    data=AptUpgradeData(
                        binary_packages=["bin4"],
                        source_packages=["pkg3"],
                    ),
                    order=6,
                ),
            ],
            warnings=[],
            error=None,
        )

        assert expected_plan == fix_plan_cve(
            issue_id="cve-1234-1235", cfg=mock.MagicMock()
        )

    @mock.patch("ubuntupro.apt.get_pkg_candidate_version")
    @mock.patch("ubuntupro.apt.compare_versions")
    @mock.patch("ubuntupro.api.u.pro.security.fix._get_cve_data")
    @mock.patch(
        "ubuntupro.api.u.pro.security.fix.query_installed_source_pkg_versions"
    )
    @mock.patch(
        "ubuntupro.api.u.pro.security.fix._check_cve_fixed_by_livepatch"
    )
    def test_fix_plan_for_cve_when_package_cannot_be_installed(
        self,
        m_check_cve_fixed_by_livepatch,
        m_query_installed_pkgs,
        m_get_cve_data,
        m_apt_compare_versions,
        m_get_pkg_candidate_version,
    ):
        m_check_cve_fixed_by_livepatch.return_value = (None, None)
        m_query_installed_pkgs.return_value = {
            "pkg1": {
                "bin1": "1.0",
                "bin2": "1.1",
            },
        }
        m_get_cve_data.return_value = (
            {
                "pkg1": CVEPackageStatus(
                    cve_response={
                        "status": "released",
                        "pocket": "security",
                    }
                ),
            },
            {
                "pkg1": {
                    "source": {
                        "description": "description",
                        "name": "pkg1",
                        "is_source": True,
                        "version": "1.1",
                    },
                    "bin1": {
                        "is_source": False,
                        "name": "bin1",
                        "version": "1.1",
                    },
                    "bin2": {
                        "is_source": False,
                        "name": "bin2",
                        "version": "1.2",
                    },
                },
            },
        )
        m_apt_compare_versions.side_effect = [False, False, True, False]
        m_get_pkg_candidate_version.side_effect = ["1.1", "1.1"]

        expected_plan = FixPlanResult(
            title="CVE-1234-1235",
            expected_status=str(FixStatus.SYSTEM_STILL_VULNERABLE),
            plan=[
                FixPlanAptUpgradeStep(
                    data=AptUpgradeData(
                        binary_packages=["bin1"],
                        source_packages=["pkg1"],
                    ),
                    order=2,
                ),
            ],
            warnings=[
                FixPlanWarningPackageCannotBeInstalled(
                    data=PackageCannotBeInstalledData(
                        binary_package="bin2",
                        source_package="pkg1",
                        binary_package_version="1.2",
                    ),
                    order=1,
                )
            ],
            error=None,
        )
        assert expected_plan == fix_plan_cve(
            issue_id="cve-1234-1235", cfg=mock.MagicMock()
        )

    @mock.patch("ubuntupro.apt.get_pkg_candidate_version")
    @mock.patch("ubuntupro.apt.compare_versions")
    @mock.patch("ubuntupro.api.u.pro.security.fix._get_cve_data")
    @mock.patch(
        "ubuntupro.api.u.pro.security.fix.query_installed_source_pkg_versions"
    )
    @mock.patch(
        "ubuntupro.api.u.pro.security.fix._check_cve_fixed_by_livepatch"
    )
    def test_fix_plan_for_cve_with_not_released_status(
        self,
        m_check_cve_fixed_by_livepatch,
        m_query_installed_pkgs,
        m_get_cve_data,
        m_apt_compare_versions,
        m_get_pkg_candidate_version,
    ):
        m_check_cve_fixed_by_livepatch.return_value = (None, None)
        m_query_installed_pkgs.return_value = {
            "pkg1": {
                "bin1": "1.0",
                "bin2": "1.1",
            },
            "pkg2": {
                "bin3": "1.2",
            },
        }
        m_get_cve_data.return_value = (
            {
                "pkg1": CVEPackageStatus(
                    cve_response={
                        "status": "released",
                        "pocket": "security",
                    }
                ),
                "pkg2": CVEPackageStatus(
                    cve_response={
                        "status": "needed",
                        "pocket": "updates",
                    }
                ),
            },
            {
                "pkg1": {
                    "source": {
                        "description": "description",
                        "name": "pkg1",
                        "is_source": True,
                        "version": "1.1",
                    },
                    "bin1": {
                        "is_source": False,
                        "name": "bin1",
                        "version": "1.1",
                    },
                    "bin2": {
                        "is_source": False,
                        "name": "bin2",
                        "version": "1.2",
                    },
                }
            },
        )
        m_apt_compare_versions.side_effect = [False, False, True, True]
        m_get_pkg_candidate_version.side_effect = ["1.1", "1.2"]

        expected_plan = FixPlanResult(
            title="CVE-1234-1235",
            expected_status=str(FixStatus.SYSTEM_STILL_VULNERABLE),
            plan=[
                FixPlanAptUpgradeStep(
                    data=AptUpgradeData(
                        binary_packages=["bin1", "bin2"],
                        source_packages=["pkg1"],
                    ),
                    order=2,
                ),
            ],
            warnings=[
                FixPlanWarningSecurityIssueNotFixed(
                    data=SecurityIssueNotFixedData(
                        source_packages=["pkg2"],
                        status="needed",
                    ),
                    order=1,
                )
            ],
            error=None,
        )

        assert expected_plan == fix_plan_cve(
            issue_id="cve-1234-1235", cfg=mock.MagicMock()
        )

    @mock.patch("ubuntupro.apt.get_pkg_candidate_version")
    @mock.patch("ubuntupro.apt.compare_versions")
    @mock.patch(
        "ubuntupro.api.u.pro.security.fix.merge_usn_released_binary_package_versions"  # noqa
    )
    @mock.patch(
        "ubuntupro.api.u.pro.security.fix.get_affected_packages_from_usn"
    )
    @mock.patch("ubuntupro.api.u.pro.security.fix._get_usn_data")
    @mock.patch(
        "ubuntupro.api.u.pro.security.fix.query_installed_source_pkg_versions"
    )
    def test_fix_plan_for_usn(
        self,
        m_query_installed_pkgs,
        m_get_usn_data,
        m_get_affected_packages_from_usn,
        m_merge_usn_released_binary_package,
        m_apt_compare_versions,
        m_get_pkg_candidate_version,
    ):
        m_query_installed_pkgs.return_value = {
            "pkg1": {
                "bin1": "1.0",
                "bin2": "1.1",
            },
            "pkg2": {
                "bin3": "1.2",
            },
            "pkg3": {
                "bin4": "1.3",
            },
        }
        m_get_usn_data.return_value = (
            mock.MagicMock(),
            [
                mock.MagicMock(id="USN-2345-1"),
                mock.MagicMock(id="USN-3456-8"),
            ],
        )

        m_get_affected_packages_from_usn.side_effect = [
            {
                "pkg1": CVEPackageStatus(
                    cve_response={
                        "status": "released",
                        "pocket": "security",
                    }
                ),
            },
            {
                "pkg2": CVEPackageStatus(
                    cve_response={
                        "status": "released",
                        "pocket": "security",
                    }
                ),
            },
            {
                "pkg3": CVEPackageStatus(
                    cve_response={
                        "status": "released",
                        "pocket": "security",
                    }
                ),
            },
        ]
        m_merge_usn_released_binary_package.side_effect = [
            {
                "pkg1": {
                    "source": {
                        "description": "description",
                        "name": "pkg1",
                        "is_source": True,
                        "version": "1.1",
                    },
                    "bin1": {
                        "is_source": False,
                        "name": "bin1",
                        "version": "1.1",
                    },
                    "bin2": {
                        "is_source": False,
                        "name": "bin2",
                        "version": "1.2",
                    },
                },
            },
            {
                "pkg2": {
                    "source": {
                        "description": "description",
                        "name": "pkg2",
                        "is_source": True,
                        "version": "1.3",
                    },
                    "bin3": {
                        "is_source": False,
                        "name": "bin3",
                        "version": "1.3",
                    },
                },
            },
            {
                "pkg3": {
                    "source": {
                        "description": "description",
                        "name": "pkg3",
                        "is_source": True,
                        "version": "1.4",
                    },
                    "bin4": {
                        "is_source": False,
                        "name": "bin4",
                        "version": "1.4",
                    },
                }
            },
        ]
        m_apt_compare_versions.side_effect = [
            False,
            False,
            True,
            True,
            False,
            True,
            False,
            True,
        ]
        m_get_pkg_candidate_version.side_effect = ["1.1", "1.2", "1.3", "1.4"]

        expected_plan = FixPlanUSNResult(
            target_usn_plan=FixPlanResult(
                title="USN-1234-1",
                expected_status=str(FixStatus.SYSTEM_NON_VULNERABLE),
                plan=[
                    FixPlanAptUpgradeStep(
                        data=AptUpgradeData(
                            binary_packages=["bin1", "bin2"],
                            source_packages=["pkg1"],
                        ),
                        order=1,
                    ),
                ],
                warnings=[],
                error=None,
            ),
            related_usns_plan=[
                FixPlanResult(
                    title="USN-2345-1",
                    expected_status=str(FixStatus.SYSTEM_NON_VULNERABLE),
                    plan=[
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["bin3"],
                                source_packages=["pkg2"],
                            ),
                            order=1,
                        ),
                    ],
                    warnings=[],
                    error=None,
                ),
                FixPlanResult(
                    title="USN-3456-8",
                    expected_status=str(FixStatus.SYSTEM_NON_VULNERABLE),
                    plan=[
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["bin4"],
                                source_packages=["pkg3"],
                            ),
                            order=1,
                        ),
                    ],
                    warnings=[],
                    error=None,
                ),
            ],
        )

        assert expected_plan == fix_plan_usn(
            issue_id="usn-1234-1", cfg=mock.MagicMock()
        )

    @mock.patch("ubuntupro.apt.get_pkg_candidate_version")
    @mock.patch("ubuntupro.apt.compare_versions")
    @mock.patch("ubuntupro.api.u.pro.security.fix._get_cve_data")
    @mock.patch(
        "ubuntupro.api.u.pro.security.fix.query_installed_source_pkg_versions"
    )
    @mock.patch(
        "ubuntupro.api.u.pro.security.fix._check_cve_fixed_by_livepatch"
    )
    def test_fix_plan_for_cve_when_package_already_installed(
        self,
        m_check_cve_fixed_by_livepatch,
        m_query_installed_pkgs,
        m_get_cve_data,
        m_apt_compare_versions,
        m_get_pkg_candidate_version,
    ):
        m_check_cve_fixed_by_livepatch.return_value = (None, None)
        m_query_installed_pkgs.return_value = {
            "pkg1": {
                "bin1": "1.0",
                "bin2": "1.1",
            },
        }
        m_get_cve_data.return_value = (
            {
                "pkg1": CVEPackageStatus(
                    cve_response={
                        "status": "released",
                        "pocket": "security",
                    }
                ),
            },
            {
                "pkg1": {
                    "source": {
                        "description": "description",
                        "name": "pkg1",
                        "is_source": True,
                        "version": "1.0",
                    },
                    "bin1": {
                        "is_source": False,
                        "name": "bin1",
                        "version": "1.0",
                    },
                    "bin2": {
                        "is_source": False,
                        "name": "bin2",
                        "version": "1.1",
                    },
                },
            },
        )
        m_apt_compare_versions.side_effect = [True, True]
        m_get_pkg_candidate_version.side_effect = ["1.1", "1.1"]

        expected_plan = FixPlanResult(
            title="CVE-1234-1235",
            expected_status=str(FixStatus.SYSTEM_NON_VULNERABLE),
            plan=[
                FixPlanNoOpStep(
                    data=NoOpData(
                        status="cve-already-fixed",
                    ),
                    order=1,
                ),
            ],
            warnings=[],
            error=None,
        )
        assert expected_plan == fix_plan_cve(
            issue_id="cve-1234-1235", cfg=mock.MagicMock()
        )
