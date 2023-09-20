import mock
import pytest

from uaclient import messages
from uaclient.api.u.pro.security.fix import (
    ESM_INFRA_POCKET,
    STANDARD_UPDATES_POCKET,
    AptUpgradeData,
    AttachData,
    EnableData,
    FixPlanAptUpgradeStep,
    FixPlanAttachStep,
    FixPlanEnableStep,
    FixPlanError,
    FixPlanNoOpStatus,
    FixPlanNoOpStep,
    FixPlanResult,
    FixPlanWarningPackageCannotBeInstalled,
    FixPlanWarningSecurityIssueNotFixed,
    FixWarningType,
    NoOpData,
    PackageCannotBeInstalledData,
    SecurityIssueNotFixedData,
)
from uaclient.api.u.pro.security.fix.common.execute.v1 import (
    FailedUpgrade,
    FixExecuteError,
    FixExecuteResult,
    UpgradedPackage,
    _execute_fix,
)
from uaclient.security import FixStatus


class TestExecute:
    @pytest.mark.parametrize(
        "security_issue,expected_result,pkg_version",
        (
            # Attach step
            (
                FixPlanResult(
                    title="CVE-12345-567",
                    description="description",
                    expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
                    affected_packages=["pkg1", "pkg2"],
                    plan=[
                        FixPlanAttachStep(
                            data=AttachData(
                                reason="test",
                                required_service=ESM_INFRA_POCKET,
                                source_packages=["pkg1", "pkg2"],
                            ),
                            order=1,
                        ),
                        FixPlanEnableStep(
                            data=EnableData(
                                service=ESM_INFRA_POCKET,
                                source_packages=["pkg1", "pkg2"],
                            ),
                            order=2,
                        ),
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["pkg1", "pkg2"],
                                source_packages=["pkg1", "pkg2"],
                                pocket=ESM_INFRA_POCKET,
                            ),
                            order=3,
                        ),
                    ],
                    warnings=None,
                    error=None,
                    additional_data=None,
                ),
                FixExecuteResult(
                    title="CVE-12345-567",
                    description="description",
                    status=FixStatus.SYSTEM_STILL_VULNERABLE.value.msg,
                    upgraded_packages=[],
                    errors=[
                        FixExecuteError(
                            error_type="fix-requires-attach",
                            reason=messages.SECURITY_UPDATE_NOT_INSTALLED_SUBSCRIPTION,  # noqa
                            failed_upgrades=[
                                FailedUpgrade(
                                    name="pkg1", pocket=ESM_INFRA_POCKET
                                ),
                                FailedUpgrade(
                                    name="pkg2", pocket=ESM_INFRA_POCKET
                                ),
                            ],
                        )
                    ],
                ),
                None,
            ),
            # Enable step without attach
            (
                FixPlanResult(
                    title="CVE-12345-567",
                    description="description",
                    expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
                    affected_packages=["pkg1", "pkg2"],
                    plan=[
                        FixPlanEnableStep(
                            data=EnableData(
                                service=ESM_INFRA_POCKET,
                                source_packages=["pkg1", "pkg2"],
                            ),
                            order=1,
                        ),
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["pkg1", "pkg2"],
                                source_packages=["pkg1", "pkg2"],
                                pocket=ESM_INFRA_POCKET,
                            ),
                            order=2,
                        ),
                    ],
                    warnings=None,
                    error=None,
                    additional_data=None,
                ),
                FixExecuteResult(
                    title="CVE-12345-567",
                    description="description",
                    status=FixStatus.SYSTEM_STILL_VULNERABLE.value.msg,
                    upgraded_packages=[],
                    errors=[
                        FixExecuteError(
                            error_type="fix-requires-enable",
                            reason=messages.SECURITY_SERVICE_DISABLED.format(
                                service=ESM_INFRA_POCKET
                            ),
                            failed_upgrades=[
                                FailedUpgrade(
                                    name="pkg1", pocket=ESM_INFRA_POCKET
                                ),
                                FailedUpgrade(
                                    name="pkg2", pocket=ESM_INFRA_POCKET
                                ),
                            ],
                        )
                    ],
                ),
                None,
            ),
            # Package cannot be installed warning
            (
                FixPlanResult(
                    title="CVE-12345-567",
                    description="description",
                    expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
                    affected_packages=["pkg1", "pkg2"],
                    plan=[
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["bin2"],
                                source_packages=["pkg2"],
                                pocket=STANDARD_UPDATES_POCKET,
                            ),
                            order=2,
                        ),
                    ],
                    warnings=[
                        FixPlanWarningPackageCannotBeInstalled(
                            data=PackageCannotBeInstalledData(
                                binary_package="bin1",
                                binary_package_version="ver1",
                                source_package="pkg1",
                                related_source_packages=["pkg1", "pkg2"],
                                pocket=STANDARD_UPDATES_POCKET,
                            ),
                            order=1,
                        )
                    ],
                    error=None,
                    additional_data=None,
                ),
                FixExecuteResult(
                    title="CVE-12345-567",
                    description="description",
                    status=FixStatus.SYSTEM_STILL_VULNERABLE.value.msg,
                    upgraded_packages=[
                        UpgradedPackage(
                            name="bin2",
                            version="ver2",
                            pocket=STANDARD_UPDATES_POCKET,
                        )
                    ],
                    errors=[
                        FixExecuteError(
                            error_type=FixWarningType.PACKAGE_CANNOT_BE_INSTALLED.value,  # noqa
                            reason=messages.FIX_CANNOT_INSTALL_PACKAGE.format(
                                package="bin1",
                                version="ver1",
                            ),
                            failed_upgrades=[
                                FailedUpgrade(
                                    name="bin1", pocket=STANDARD_UPDATES_POCKET
                                ),
                            ],
                        )
                    ],
                ),
                "ver2",
            ),
            # Security issue not fixed warning
            (
                FixPlanResult(
                    title="CVE-12345-567",
                    description="description",
                    expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
                    affected_packages=["pkg1", "pkg2"],
                    plan=[
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["bin2"],
                                source_packages=["pkg2"],
                                pocket=STANDARD_UPDATES_POCKET,
                            ),
                            order=2,
                        ),
                    ],
                    warnings=[
                        FixPlanWarningSecurityIssueNotFixed(
                            data=SecurityIssueNotFixedData(
                                source_packages=["pkg1"], status="pending"
                            ),
                            order=1,
                        )
                    ],
                    error=None,
                    additional_data=None,
                ),
                FixExecuteResult(
                    title="CVE-12345-567",
                    description="description",
                    status=FixStatus.SYSTEM_STILL_VULNERABLE.value.msg,
                    upgraded_packages=[
                        UpgradedPackage(
                            name="bin2",
                            version="ver2",
                            pocket=STANDARD_UPDATES_POCKET,
                        )
                    ],
                    errors=[
                        FixExecuteError(
                            error_type=FixWarningType.SECURITY_ISSUE_NOT_FIXED.value,  # noqa
                            reason=messages.SECURITY_CVE_STATUS_PENDING,
                            failed_upgrades=[
                                FailedUpgrade(name="pkg1"),
                            ],
                        )
                    ],
                ),
                "ver2",
            ),
            # CVE error
            (
                FixPlanResult(
                    title="CVE-1",
                    description=None,
                    expected_status="error",
                    affected_packages=None,
                    plan=[
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["bin2"],
                                source_packages=["pkg2"],
                                pocket=STANDARD_UPDATES_POCKET,
                            ),
                            order=2,
                        ),
                    ],
                    warnings=[],
                    error=FixPlanError(
                        code="security-issue-not-found-issue",
                        msg=messages.E_SECURITY_FIX_NOT_FOUND_ISSUE.format(
                            issue_id="CVE-"
                        ),
                    ),
                    additional_data=None,
                ),
                FixExecuteResult(
                    title="CVE-1",
                    description=None,
                    status="error",
                    upgraded_packages=[],
                    errors=[
                        FixExecuteError(
                            error_type="security-issue-not-found-issue",
                            reason=messages.E_SECURITY_FIX_NOT_FOUND_ISSUE.format(  # noqa
                                issue_id="CVE-"
                            ),
                        )
                    ],
                ),
                None,
            ),
            # Noop step
            (
                FixPlanResult(
                    title="CVE-12345-567",
                    description="description",
                    expected_status=FixStatus.SYSTEM_NOT_AFFECTED.value.msg,
                    affected_packages=["pkg1", "pkg2"],
                    plan=[
                        FixPlanNoOpStep(
                            data=NoOpData(
                                status=FixPlanNoOpStatus.NOT_AFFECTED.value
                            ),
                            order=1,
                        )
                    ],
                    warnings=[],
                    error=None,
                    additional_data=None,
                ),
                FixExecuteResult(
                    title="CVE-12345-567",
                    description="description",
                    status=FixStatus.SYSTEM_NOT_AFFECTED.value.msg,
                    upgraded_packages=[],
                    errors=None,
                ),
                None,
            ),
        ),
    )
    @mock.patch("uaclient.apt.run_apt_update_command")
    @mock.patch("uaclient.apt.run_apt_command")
    @mock.patch("uaclient.apt.get_pkg_version")
    def test_execute(
        self,
        m_get_pkg_version,
        _m_run_apt_cmd,
        _m_run_apt_update,
        security_issue,
        expected_result,
        pkg_version,
    ):
        m_get_pkg_version.return_value = pkg_version
        assert expected_result == _execute_fix(security_issue)
