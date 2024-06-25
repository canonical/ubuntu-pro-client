from typing import List, Optional

from uaclient import apt, messages, util
from uaclient.api.u.pro.security.fix._common import FixStatus, status_message
from uaclient.api.u.pro.security.fix._common.plan.v1 import (
    FixPlanAptUpgradeStep,
    FixPlanAttachStep,
    FixPlanEnableStep,
    FixPlanNoOpStatus,
    FixPlanNoOpStep,
    FixPlanResult,
    FixPlanWarningPackageCannotBeInstalled,
    FixPlanWarningSecurityIssueNotFixed,
)
from uaclient.data_types import DataObject, Field, StringDataValue, data_list


class UpgradedPackage(DataObject):
    fields = [
        Field("name", StringDataValue, doc="The name of the package"),
        Field(
            "version",
            StringDataValue,
            doc="The version that the package was upgraded to",
        ),
        Field(
            "pocket",
            StringDataValue,
            doc="The pocket which contained the package upgrade",
        ),
    ]

    def __init__(self, name: str, version: str, pocket: str):
        self.name = name
        self.version = version
        self.pocket = pocket


class FailedUpgrade(DataObject):
    fields = [
        Field("name", StringDataValue, doc="The name of the package"),
        Field(
            "pocket",
            StringDataValue,
            required=False,
            doc="The pocket which contained the package upgrade",
        ),
    ]

    def __init__(self, name: str, pocket: Optional[str] = None):
        self.name = name
        self.pocket = pocket


class FixExecuteError(DataObject):
    fields = [
        Field("error_type", StringDataValue, doc="The type of the error"),
        Field(
            "reason", StringDataValue, doc="The reason why the error occurred"
        ),
        Field(
            "failed_upgrades",
            data_list(FailedUpgrade),
            required=False,
            doc="A list of ``FailedUpgrade`` objects",
        ),
    ]

    def __init__(
        self,
        error_type: str,
        reason: str,
        failed_upgrades: Optional[List[FailedUpgrade]] = None,
    ):
        self.error_type = error_type
        self.reason = reason
        self.failed_upgrades = failed_upgrades


class FixExecuteResult(DataObject):
    fields = [
        Field("title", StringDataValue, doc="The title of the CVE"),
        Field(
            "description",
            StringDataValue,
            required=False,
            doc="The description of the CVE",
        ),
        Field("status", StringDataValue, doc="The status of fixing the CVE"),
        Field(
            "upgraded_packages",
            data_list(UpgradedPackage),
            required=False,
            doc="A list of ``UpgradedPackage`` objects",
        ),
        Field(
            "errors",
            data_list(FixExecuteError),
            required=False,
            doc="A list of ``FixExecuteError`` objects",
        ),
    ]

    def __init__(
        self,
        title: str,
        status: str,
        description: Optional[str] = None,
        upgraded_packages: Optional[List[UpgradedPackage]] = None,
        errors: Optional[List[FixExecuteError]] = None,
    ):
        self.title = title
        self.description = description
        self.status = status
        self.upgraded_packages = upgraded_packages
        self.errors = errors


class ExecuteContext:
    def __init__(self):
        self.require_enable = False
        self.require_attach = False
        self.status = FixStatus.SYSTEM_NON_VULNERABLE.value.msg
        self.upgraded_pkgs = []  # type: List[UpgradedPackage]
        self.errors = []  # type: List[FixExecuteError]


def _handle_error(
    execute_context: ExecuteContext, security_issue: FixPlanResult
):
    if security_issue.error:
        execute_context.errors.append(
            FixExecuteError(
                error_type=security_issue.error.code or "unexpected-error",
                reason=security_issue.error.msg,
            )
        )
        execute_context.status = "error"


def _handle_security_issue_not_fixed(
    execute_context: ExecuteContext,
    warning: FixPlanWarningSecurityIssueNotFixed,
):
    execute_context.errors.append(
        FixExecuteError(
            error_type=warning.warning_type,
            reason=status_message(warning.data.status),
            failed_upgrades=[
                FailedUpgrade(name=pkg) for pkg in warning.data.source_packages
            ],
        )
    )
    execute_context.status = FixStatus.SYSTEM_STILL_VULNERABLE.value.msg


def _handle_package_cannot_be_installed(
    execute_context: ExecuteContext,
    warning: FixPlanWarningPackageCannotBeInstalled,
):
    execute_context.errors.append(
        FixExecuteError(
            error_type=warning.warning_type,
            reason=messages.FIX_CANNOT_INSTALL_PACKAGE.format(
                package=warning.data.binary_package,
                version=warning.data.binary_package_version,
            ),
            failed_upgrades=[
                FailedUpgrade(
                    name=warning.data.binary_package,
                    pocket=warning.data.pocket,
                )
            ],
        )
    )
    execute_context.status = FixStatus.SYSTEM_STILL_VULNERABLE.value.msg


def _handle_attach(execute_context: ExecuteContext, step: FixPlanAttachStep):
    execute_context.errors.append(
        FixExecuteError(
            error_type="fix-requires-attach",
            reason=messages.SECURITY_UPDATE_NOT_INSTALLED_SUBSCRIPTION,
            failed_upgrades=[
                FailedUpgrade(name=pkg, pocket=step.data.required_service)
                for pkg in step.data.source_packages
            ],
        )
    )
    execute_context.require_attach = True
    execute_context.status = FixStatus.SYSTEM_STILL_VULNERABLE.value.msg


def _handle_enable(execute_context: ExecuteContext, step: FixPlanEnableStep):
    if execute_context.require_attach:
        return

    execute_context.errors.append(
        FixExecuteError(
            error_type="fix-requires-enable",
            reason=messages.SECURITY_SERVICE_DISABLED.format(
                service=step.data.service
            ),
            failed_upgrades=[
                FailedUpgrade(name=pkg, pocket=step.data.service)
                for pkg in step.data.source_packages
            ],
        )
    )
    execute_context.require_enable = True
    execute_context.status = FixStatus.SYSTEM_STILL_VULNERABLE.value.msg


def _handle_apt_upgrade(
    execute_context: ExecuteContext, step: FixPlanAptUpgradeStep
):
    if execute_context.require_attach or execute_context.require_enable:
        return

    if not step.data.binary_packages:
        return

    if not util.we_are_currently_root():
        execute_context.errors.append(
            FixExecuteError(
                error_type="fix-require-root",
                reason=messages.SECURITY_APT_NON_ROOT,
                failed_upgrades=[
                    FailedUpgrade(name=pkg, pocket=step.data.pocket)
                    for pkg in step.data.source_packages
                ],
            )
        )
        execute_context.status = "error"
        return

    try:
        apt.run_apt_update_command()
        apt.run_apt_command(
            cmd=["apt-get", "install", "--only-upgrade", "-y"]
            + step.data.binary_packages,
            override_env_vars={"DEBIAN_FRONTEND": "noninteractive"},
        )

        for pkg in step.data.binary_packages:
            pkg_version = apt.get_pkg_version(pkg)

            if pkg_version:
                execute_context.upgraded_pkgs.append(
                    UpgradedPackage(
                        name=pkg,
                        version=pkg_version,
                        pocket=step.data.pocket,
                    )
                )

    except Exception as e:
        msg = getattr(e, "msg", str(e))
        execute_context.status = FixStatus.SYSTEM_STILL_VULNERABLE.value.msg
        execute_context.errors.append(
            FixExecuteError(
                error_type="fix-error-installing-pkg",
                reason=msg,
                failed_upgrades=[
                    FailedUpgrade(name=pkg, pocket=step.data.pocket)
                    for pkg in step.data.source_packages
                ],
            )
        )


def _handle_noop(execute_context: ExecuteContext, step: FixPlanNoOpStep):
    if step.data.status == FixPlanNoOpStatus.NOT_AFFECTED.value:
        execute_context.status = FixStatus.SYSTEM_NOT_AFFECTED.value.msg


def _execute_fix(security_issue: FixPlanResult) -> FixExecuteResult:
    execute_context = ExecuteContext()

    if security_issue.error:
        _handle_error(execute_context, security_issue)

    if security_issue.warnings:
        for warning in security_issue.warnings:
            if isinstance(warning, FixPlanWarningSecurityIssueNotFixed):
                _handle_security_issue_not_fixed(execute_context, warning)
            elif isinstance(warning, FixPlanWarningPackageCannotBeInstalled):
                _handle_package_cannot_be_installed(execute_context, warning)

    if security_issue.plan:
        for step in security_issue.plan:
            if isinstance(step, FixPlanAttachStep):
                _handle_attach(execute_context, step)
            elif isinstance(step, FixPlanEnableStep):
                _handle_enable(execute_context, step)
            elif isinstance(step, FixPlanAptUpgradeStep):
                _handle_apt_upgrade(execute_context, step)
            elif isinstance(step, FixPlanNoOpStep):
                _handle_noop(execute_context, step)

    return FixExecuteResult(
        title=security_issue.title,
        description=security_issue.description,
        status=execute_context.status,
        upgraded_packages=execute_context.upgraded_pkgs,
        errors=None if not execute_context.errors else execute_context.errors,
    )
