import mock
import pytest

from uaclient.api.u.pro.security.fix import (
    AdditionalData,
    AptUpgradeData,
    AttachData,
    EnableData,
    FixPlanAptUpgradeStep,
    FixPlanAttachStep,
    FixPlanEnableStep,
    FixPlanError,
    FixPlanNoOpAlreadyFixedStep,
    FixPlanNoOpLivepatchFixStep,
    FixPlanNoOpStep,
    FixPlanResult,
    FixPlanUSNResult,
    FixPlanWarningPackageCannotBeInstalled,
    FixPlanWarningSecurityIssueNotFixed,
    NoOpAlreadyFixedData,
    NoOpData,
    NoOpLivepatchFixData,
    PackageCannotBeInstalledData,
    SecurityIssueNotFixedData,
    USNAdditionalData,
    fix_plan_cve,
    fix_plan_usn,
)
from uaclient.api.u.pro.status.enabled_services.v1 import EnabledService
from uaclient.contract import ContractExpiryStatus
from uaclient.messages import INVALID_SECURITY_ISSUE
from uaclient.security import CVEPackageStatus, FixStatus

M_PATH = "uaclient.api.u.pro.security.fix."


class TestFixPlan:
    @pytest.mark.parametrize(
        "issue_id", (("CVE-sdsa"), ("test"), (""), (None))
    )
    def test_fix_plan_cve_invalid_security_issue(self, issue_id):
        expected_plan = FixPlanResult(
            title=issue_id,
            description=None,
            expected_status="error",
            affected_packages=None,
            plan=[],
            warnings=[],
            error=FixPlanError(
                msg=INVALID_SECURITY_ISSUE.format(issue_id=issue_id).msg,
                code=INVALID_SECURITY_ISSUE.name,
            ),
            additional_data=AdditionalData(),
        )
        assert expected_plan == fix_plan_cve(issue_id, cfg=mock.MagicMock())

    @pytest.mark.parametrize(
        "issue_id", (("USN-sadsa"), ("test"), (""), (None))
    )
    def test_fix_plan_usn_invalid_security_issue(self, issue_id):
        expected_plan = FixPlanUSNResult(
            target_usn_plan=FixPlanResult(
                title=issue_id,
                description=None,
                expected_status="error",
                affected_packages=None,
                plan=[],
                warnings=[],
                error=FixPlanError(
                    msg=INVALID_SECURITY_ISSUE.format(issue_id=issue_id).msg,
                    code=INVALID_SECURITY_ISSUE.name,
                ),
                additional_data=AdditionalData(),
            ),
            related_usns_plan=[],
        )
        assert expected_plan == fix_plan_usn(issue_id, cfg=mock.MagicMock())

    @mock.patch(
        "uaclient.api.u.pro.security.fix._check_cve_fixed_by_livepatch"
    )
    def test_fix_plan_cve_fixed_by_livepatch(
        self,
        m_check_cve_fixed_by_livepatch,
    ):
        m_check_cve_fixed_by_livepatch.return_value = (
            FixStatus.SYSTEM_NON_VULNERABLE,
            "1.0",
        )
        expected_plan = FixPlanResult(
            title="CVE-1234-1235",
            description=None,
            expected_status=str(FixStatus.SYSTEM_NON_VULNERABLE),
            affected_packages=None,
            plan=[
                FixPlanNoOpLivepatchFixStep(
                    data=NoOpLivepatchFixData(
                        status="cve-fixed-by-livepatch",
                        patch_version="1.0",
                    ),
                    order=1,
                )
            ],
            warnings=[],
            error=None,
            additional_data=AdditionalData(),
        )

        assert expected_plan == fix_plan_cve(
            issue_id="cve-1234-1235", cfg=mock.MagicMock()
        )

    @mock.patch(M_PATH + "merge_usn_released_binary_package_versions")
    @mock.patch(M_PATH + "get_cve_affected_source_packages_status")
    @mock.patch(M_PATH + "_get_cve_data")
    @mock.patch(M_PATH + "query_installed_source_pkg_versions")
    @mock.patch(M_PATH + "_check_cve_fixed_by_livepatch")
    def test_fix_plan_for_no_affected_packages(
        self,
        m_check_cve_fixed_by_livepatch,
        m_query_installed_pkgs,
        m_get_cve_data,
        m_get_cve_affected_pkgs,
        m_merge_usn_pkgs,
    ):
        m_check_cve_fixed_by_livepatch.return_value = (None, None)
        m_query_installed_pkgs.return_value = {
            "pkg1": {
                "bin1": "1.0",
                "bin2": "1.1",
            }
        }
        m_get_cve_data.return_value = (
            mock.MagicMock(
                description="descr",
                notices=[mock.MagicMock(title="test")],
            ),
            [],
        )
        m_get_cve_affected_pkgs.return_value = {}
        m_merge_usn_pkgs.return_value = {}
        expected_plan = FixPlanResult(
            title="CVE-1234-1235",
            description="test",
            expected_status=str(FixStatus.SYSTEM_NOT_AFFECTED),
            affected_packages=[],
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
            additional_data=AdditionalData(),
        )

        assert expected_plan == fix_plan_cve(
            issue_id="cve-1234-1235", cfg=mock.MagicMock()
        )

    @mock.patch(M_PATH + "merge_usn_released_binary_package_versions")
    @mock.patch(M_PATH + "get_cve_affected_source_packages_status")
    @mock.patch("uaclient.apt.get_pkg_candidate_version")
    @mock.patch(M_PATH + "_get_cve_data")
    @mock.patch(M_PATH + "query_installed_source_pkg_versions")
    @mock.patch(M_PATH + "_check_cve_fixed_by_livepatch")
    def test_fix_plan_for_cve(
        self,
        m_check_cve_fixed_by_livepatch,
        m_query_installed_pkgs,
        m_get_cve_data,
        m_get_pkg_candidate_version,
        m_get_cve_affected_pkgs,
        m_merge_usn_pkgs,
    ):
        m_check_cve_fixed_by_livepatch.return_value = (None, None)
        m_query_installed_pkgs.return_value = {
            "pkg1": {
                "bin1": "1.0",
                "bin2": "1.1",
            }
        }
        m_get_cve_data.return_value = (
            mock.MagicMock(
                description="descr",
                notices=[mock.MagicMock(title="test")],
            ),
            [],
        )
        m_get_cve_affected_pkgs.return_value = {
            "pkg1": CVEPackageStatus(
                cve_response={
                    "status": "released",
                    "pocket": "security",
                }
            ),
        }
        m_merge_usn_pkgs.return_value = {
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
        }
        m_get_pkg_candidate_version.side_effect = ["1.1", "1.2"]

        expected_plan = FixPlanResult(
            title="CVE-1234-1235",
            description="test",
            expected_status=str(FixStatus.SYSTEM_NON_VULNERABLE),
            affected_packages=["pkg1"],
            plan=[
                FixPlanAptUpgradeStep(
                    data=AptUpgradeData(
                        binary_packages=["bin1", "bin2"],
                        source_packages=["pkg1"],
                        pocket="standard-updates",
                    ),
                    order=1,
                )
            ],
            warnings=[],
            error=None,
            additional_data=AdditionalData(),
        )

        assert expected_plan == fix_plan_cve(
            issue_id="cve-1234-1235", cfg=mock.MagicMock()
        )

    @mock.patch(M_PATH + "merge_usn_released_binary_package_versions")
    @mock.patch(M_PATH + "get_cve_affected_source_packages_status")
    @mock.patch(M_PATH + "_enabled_services")
    @mock.patch(M_PATH + "_is_attached")
    @mock.patch(M_PATH + "get_contract_expiry_status")
    @mock.patch("uaclient.apt.get_pkg_candidate_version")
    @mock.patch(M_PATH + "_get_cve_data")
    @mock.patch(M_PATH + "query_installed_source_pkg_versions")
    @mock.patch(M_PATH + "_check_cve_fixed_by_livepatch")
    def test_fix_plan_for_cve_that_requires_pro_services(
        self,
        m_check_cve_fixed_by_livepatch,
        m_query_installed_pkgs,
        m_get_cve_data,
        m_get_pkg_candidate_version,
        m_get_contract_expiry_status,
        m_is_attached,
        m_enabled_services,
        m_get_cve_affected_pkgs,
        m_merge_usn_pkgs,
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
            mock.MagicMock(
                description="descr",
                notices=[],
            ),
            [],
        )
        m_get_cve_affected_pkgs.return_value = {
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
        }
        m_merge_usn_pkgs.return_value = {
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
        }
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
            mock.MagicMock(
                enabled_services=[
                    EnabledService(name="esm-infra", variant_enabled=False)
                ]
            ),
        ]

        expected_plan = FixPlanResult(
            title="CVE-1234-1235",
            description="descr",
            expected_status=str(FixStatus.SYSTEM_NON_VULNERABLE),
            affected_packages=["pkg1", "pkg2", "pkg3"],
            plan=[
                FixPlanAptUpgradeStep(
                    data=AptUpgradeData(
                        binary_packages=["bin1", "bin2"],
                        source_packages=["pkg1"],
                        pocket="standard-updates",
                    ),
                    order=1,
                ),
                FixPlanAttachStep(
                    data=AttachData(
                        reason="required-pro-service",
                        required_service="esm-infra",
                        source_packages=["pkg2"],
                    ),
                    order=2,
                ),
                FixPlanEnableStep(
                    data=EnableData(
                        service="esm-infra",
                        source_packages=["pkg2"],
                    ),
                    order=3,
                ),
                FixPlanAptUpgradeStep(
                    data=AptUpgradeData(
                        binary_packages=["bin3"],
                        source_packages=["pkg2"],
                        pocket="esm-infra",
                    ),
                    order=4,
                ),
                FixPlanEnableStep(
                    data=EnableData(
                        service="esm-apps",
                        source_packages=["pkg3"],
                    ),
                    order=5,
                ),
                FixPlanAptUpgradeStep(
                    data=AptUpgradeData(
                        binary_packages=["bin4"],
                        source_packages=["pkg3"],
                        pocket="esm-apps",
                    ),
                    order=6,
                ),
            ],
            warnings=[],
            error=None,
            additional_data=AdditionalData(),
        )

        assert expected_plan == fix_plan_cve(
            issue_id="cve-1234-1235", cfg=mock.MagicMock()
        )

    @mock.patch(M_PATH + "merge_usn_released_binary_package_versions")
    @mock.patch(M_PATH + "get_cve_affected_source_packages_status")
    @mock.patch("uaclient.apt.get_pkg_candidate_version")
    @mock.patch("uaclient.api.u.pro.security.fix._get_cve_data")
    @mock.patch(M_PATH + "query_installed_source_pkg_versions")
    @mock.patch(M_PATH + "_check_cve_fixed_by_livepatch")
    def test_fix_plan_for_cve_when_package_cannot_be_installed(
        self,
        m_check_cve_fixed_by_livepatch,
        m_query_installed_pkgs,
        m_get_cve_data,
        m_get_pkg_candidate_version,
        m_get_cve_affected_pkgs,
        m_merge_usn_pkgs,
    ):
        m_check_cve_fixed_by_livepatch.return_value = (None, None)
        m_query_installed_pkgs.return_value = {
            "pkg1": {
                "bin1": "1.0",
                "bin2": "1.1",
            },
        }
        m_get_cve_data.return_value = (
            mock.MagicMock(
                description="descr",
                notices=[mock.MagicMock(title="test")],
            ),
            [],
        )
        m_get_cve_affected_pkgs.return_value = {
            "pkg1": CVEPackageStatus(
                cve_response={
                    "status": "released",
                    "pocket": "security",
                }
            ),
        }
        m_merge_usn_pkgs.return_value = {
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
        }
        m_get_pkg_candidate_version.side_effect = ["1.1", "1.1"]

        expected_plan = FixPlanResult(
            title="CVE-1234-1235",
            description="test",
            expected_status=str(FixStatus.SYSTEM_STILL_VULNERABLE),
            affected_packages=["pkg1"],
            plan=[
                FixPlanAptUpgradeStep(
                    data=AptUpgradeData(
                        binary_packages=["bin1"],
                        source_packages=["pkg1"],
                        pocket="standard-updates",
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
                        pocket="standard-updates",
                        related_source_packages=["pkg1"],
                    ),
                    order=1,
                )
            ],
            error=None,
            additional_data=AdditionalData(),
        )
        assert expected_plan == fix_plan_cve(
            issue_id="cve-1234-1235", cfg=mock.MagicMock()
        )

    @mock.patch(M_PATH + "merge_usn_released_binary_package_versions")
    @mock.patch(M_PATH + "get_cve_affected_source_packages_status")
    @mock.patch("uaclient.apt.get_pkg_candidate_version")
    @mock.patch("uaclient.api.u.pro.security.fix._get_cve_data")
    @mock.patch(M_PATH + "query_installed_source_pkg_versions")
    @mock.patch(M_PATH + "_check_cve_fixed_by_livepatch")
    def test_fix_plan_for_cve_with_not_released_status(
        self,
        m_check_cve_fixed_by_livepatch,
        m_query_installed_pkgs,
        m_get_cve_data,
        m_get_pkg_candidate_version,
        m_get_cve_affected_pkgs,
        m_merge_usn_pkgs,
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
            mock.MagicMock(
                description="descr",
                notices=[mock.MagicMock(title="test")],
            ),
            [],
        )
        m_get_cve_affected_pkgs.return_value = {
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
        }
        m_merge_usn_pkgs.return_value = {
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
        }
        m_get_pkg_candidate_version.side_effect = ["1.1", "1.2"]

        expected_plan = FixPlanResult(
            title="CVE-1234-1235",
            description="test",
            expected_status=str(FixStatus.SYSTEM_STILL_VULNERABLE),
            affected_packages=["pkg1", "pkg2"],
            plan=[
                FixPlanAptUpgradeStep(
                    data=AptUpgradeData(
                        binary_packages=["bin1", "bin2"],
                        source_packages=["pkg1"],
                        pocket="standard-updates",
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
            additional_data=AdditionalData(),
        )

        assert expected_plan == fix_plan_cve(
            issue_id="cve-1234-1235", cfg=mock.MagicMock()
        )

    @mock.patch("uaclient.apt.get_pkg_candidate_version")
    @mock.patch(M_PATH + "merge_usn_released_binary_package_versions")
    @mock.patch(M_PATH + "get_affected_packages_from_usn")
    @mock.patch(M_PATH + "_get_usn_data")
    @mock.patch(M_PATH + "query_installed_source_pkg_versions")
    def test_fix_plan_for_usn(
        self,
        m_query_installed_pkgs,
        m_get_usn_data,
        m_get_affected_packages_from_usn,
        m_merge_usn_released_binary_package,
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
            mock.MagicMock(cves_ids=[], references=[], title="test"),
            [
                mock.MagicMock(
                    id="USN-2345-1",
                    cves_ids=["CVE-1234-12345"],
                    references=[],
                    title="test2",
                ),
                mock.MagicMock(
                    id="USN-3456-8",
                    cves_ids=[],
                    references=["https://launchpad.net/bugs/BUG"],
                    title="test3",
                ),
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
        m_get_pkg_candidate_version.side_effect = ["1.1", "1.2", "1.3", "1.4"]

        expected_plan = FixPlanUSNResult(
            target_usn_plan=FixPlanResult(
                title="USN-1234-1",
                description="test",
                affected_packages=["pkg1"],
                expected_status=str(FixStatus.SYSTEM_NON_VULNERABLE),
                plan=[
                    FixPlanAptUpgradeStep(
                        data=AptUpgradeData(
                            binary_packages=["bin1", "bin2"],
                            source_packages=["pkg1"],
                            pocket="standard-updates",
                        ),
                        order=1,
                    ),
                ],
                warnings=[],
                error=None,
                additional_data=USNAdditionalData(
                    associated_cves=[],
                    associated_launchpad_bugs=[],
                ),
            ),
            related_usns_plan=[
                FixPlanResult(
                    title="USN-2345-1",
                    description="test2",
                    expected_status=str(FixStatus.SYSTEM_NON_VULNERABLE),
                    affected_packages=["pkg2"],
                    plan=[
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["bin3"],
                                source_packages=["pkg2"],
                                pocket="standard-updates",
                            ),
                            order=1,
                        ),
                    ],
                    warnings=[],
                    error=None,
                    additional_data=USNAdditionalData(
                        associated_cves=["CVE-1234-12345"],
                        associated_launchpad_bugs=[],
                    ),
                ),
                FixPlanResult(
                    title="USN-3456-8",
                    description="test3",
                    expected_status=str(FixStatus.SYSTEM_NON_VULNERABLE),
                    affected_packages=["pkg3"],
                    plan=[
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["bin4"],
                                source_packages=["pkg3"],
                                pocket="standard-updates",
                            ),
                            order=1,
                        ),
                    ],
                    warnings=[],
                    error=None,
                    additional_data=USNAdditionalData(
                        associated_cves=[],
                        associated_launchpad_bugs=[
                            "https://launchpad.net/bugs/BUG"
                        ],
                    ),
                ),
            ],
        )

        assert expected_plan == fix_plan_usn(
            issue_id="usn-1234-1", cfg=mock.MagicMock()
        )

    @mock.patch(M_PATH + "merge_usn_released_binary_package_versions")
    @mock.patch(M_PATH + "get_cve_affected_source_packages_status")
    @mock.patch("uaclient.apt.get_pkg_candidate_version")
    @mock.patch(M_PATH + "_get_cve_data")
    @mock.patch(M_PATH + "query_installed_source_pkg_versions")
    @mock.patch(M_PATH + "_check_cve_fixed_by_livepatch")
    def test_fix_plan_for_cve_when_package_already_installed(
        self,
        m_check_cve_fixed_by_livepatch,
        m_query_installed_pkgs,
        m_get_cve_data,
        m_get_pkg_candidate_version,
        m_get_cve_affected_pkgs,
        m_merge_usn_pkgs,
    ):
        m_check_cve_fixed_by_livepatch.return_value = (None, None)
        m_query_installed_pkgs.return_value = {
            "pkg1": {
                "bin1": "1.0",
                "bin2": "1.1",
            },
        }
        m_get_cve_data.return_value = (
            mock.MagicMock(
                description="descr",
                notices=[mock.MagicMock(title="test")],
            ),
            [],
        )
        m_get_cve_affected_pkgs.return_value = {
            "pkg1": CVEPackageStatus(
                cve_response={
                    "status": "released",
                    "pocket": "security",
                }
            ),
        }
        m_merge_usn_pkgs.return_valuev = {
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
        }
        m_get_pkg_candidate_version.side_effect = ["1.1", "1.1"]

        expected_plan = FixPlanResult(
            title="CVE-1234-1235",
            description="test",
            expected_status=str(FixStatus.SYSTEM_NON_VULNERABLE),
            affected_packages=["pkg1"],
            plan=[
                FixPlanNoOpAlreadyFixedStep(
                    data=NoOpAlreadyFixedData(
                        status="cve-already-fixed",
                        source_packages=["pkg1"],
                        pocket="standard-updates",
                    ),
                    order=1,
                ),
            ],
            warnings=[],
            error=None,
            additional_data=AdditionalData(),
        )
        assert expected_plan == fix_plan_cve(
            issue_id="cve-1234-1235", cfg=mock.MagicMock()
        )
