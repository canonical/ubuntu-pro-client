import enum
import re
from collections import defaultdict
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from ubuntupro import apt, exceptions, messages
from ubuntupro.api.u.pro.status.enabled_services.v1 import _enabled_services
from ubuntupro.api.u.pro.status.is_attached.v1 import _is_attached
from ubuntupro.config import UAConfig
from ubuntupro.contract import ContractExpiryStatus, get_contract_expiry_status
from ubuntupro.data_types import (
    DataObject,
    Field,
    IntDataValue,
    StringDataValue,
    data_list,
)
from ubuntupro.security import (
    CVE_OR_USN_REGEX,
    UA_APPS_POCKET,
    UA_INFRA_POCKET,
    UBUNTU_STANDARD_UPDATES_POCKET,
    USN,
    BinaryPackageFix,
    CVEPackageStatus,
    FixStatus,
    UASecurityClient,
    _check_cve_fixed_by_livepatch,
    get_affected_packages_from_usn,
    get_cve_affected_source_packages_status,
    get_related_usns,
    group_by_usn_package_status,
    merge_usn_released_binary_package_versions,
    query_installed_source_pkg_versions,
)

UnfixedPackage = NamedTuple(
    "UnfixedPackage",
    [
        ("source_package", str),
        ("binary_package", str),
        ("version", Optional[str]),
    ],
)


@enum.unique
class FixStepType(enum.Enum):
    ATTACH = "attach"
    ENABLE = "enable"
    NOOP = "no-op"
    APT_UPGRADE = "apt-upgrade"


@enum.unique
class FixPlanNoOpStatus(enum.Enum):
    ALREADY_FIXED = "cve-already-fixed"
    NOT_AFFECTED = "system-not-affected"
    FIXED_BY_LIVEPATCH = "cve-fixed-by-livepatch"


@enum.unique
class FixPlanAttachReason(enum.Enum):
    EXPIRED_CONTRACT = "expired-contract-token"
    REQUIRED_PRO_SERVICE = "required-pro-service"


@enum.unique
class FixWarningType(enum.Enum):
    PACKAGE_CANNOT_BE_INSTALLED = "package-cannot-be-installed"
    SECURITY_ISSUE_NOT_FIXED = "security-issue-not-fixed"


class FixPlanStep(DataObject):
    fields = [
        Field("operation", StringDataValue),
        Field("order", IntDataValue),
    ]

    def __init__(self, *, operation: str, order: int):
        self.operation = operation
        self.order = order


class AptUpgradeData(DataObject):
    fields = [
        Field("binary_packages", data_list(StringDataValue)),
        Field("source_packages", data_list(StringDataValue)),
    ]

    def __init__(
        self, *, binary_packages: List[str], source_packages: List[str]
    ):
        self.binary_packages = binary_packages
        self.source_packages = source_packages


class FixPlanAptUpgradeStep(FixPlanStep):
    fields = [
        Field("operation", StringDataValue),
        Field("data", AptUpgradeData),
        Field("order", IntDataValue),
    ]

    def __init__(self, *, data: AptUpgradeData, order: int):
        super().__init__(operation=FixStepType.APT_UPGRADE.value, order=order)
        self.data = data


class AttachData(DataObject):
    fields = [
        Field("reason", StringDataValue),
    ]

    def __init__(self, *, reason: str):
        self.reason = reason


class FixPlanAttachStep(FixPlanStep):
    fields = [
        Field("operation", StringDataValue),
        Field("data", AttachData),
        Field("order", IntDataValue),
    ]

    def __init__(self, *, data: AttachData, order: int):
        super().__init__(operation=FixStepType.ATTACH.value, order=order)
        self.data = data


class EnableData(DataObject):
    fields = [
        Field("service", StringDataValue),
    ]

    def __init__(self, *, service: str):
        self.service = service


class FixPlanEnableStep(FixPlanStep):
    fields = [
        Field("operation", StringDataValue),
        Field("data", EnableData),
        Field("order", IntDataValue),
    ]

    def __init__(self, *, data: EnableData, order: int):
        super().__init__(operation=FixStepType.ENABLE.value, order=order)
        self.data = data


class NoOpData(DataObject):
    fields = [
        Field("status", StringDataValue),
    ]

    def __init__(self, *, status: str):
        self.status = status


class FixPlanNoOpStep(FixPlanStep):
    fields = [
        Field("operation", StringDataValue),
        Field("data", NoOpData),
        Field("order", IntDataValue),
    ]

    def __init__(self, *, data: NoOpData, order: int):
        super().__init__(operation=FixStepType.NOOP.value, order=order)
        self.data = data


class FixPlanWarning(DataObject):
    fields = [
        Field("warning_type", StringDataValue),
        Field("order", IntDataValue),
    ]

    def __init__(self, *, warning_type: str, order: int):
        self.warning_type = warning_type
        self.order = order


class SecurityIssueNotFixedData(DataObject):
    fields = [
        Field("source_packages", data_list(StringDataValue)),
        Field("status", StringDataValue),
    ]

    def __init__(self, *, source_packages: List[str], status: str):
        self.source_packages = source_packages
        self.status = status


class FixPlanWarningSecurityIssueNotFixed(FixPlanWarning):
    fields = [
        Field("warning_type", StringDataValue),
        Field("order", IntDataValue),
        Field("data", SecurityIssueNotFixedData),
    ]

    def __init__(self, *, order: int, data: SecurityIssueNotFixedData):
        super().__init__(
            warning_type=FixWarningType.SECURITY_ISSUE_NOT_FIXED.value,
            order=order,
        )
        self.data = data


class PackageCannotBeInstalledData(DataObject):
    fields = [
        Field("binary_package", StringDataValue),
        Field("binary_package_version", StringDataValue),
        Field("source_package", StringDataValue),
    ]

    def __init__(
        self,
        *,
        binary_package: str,
        binary_package_version: str,
        source_package: str
    ):
        self.source_package = source_package
        self.binary_package = binary_package
        self.binary_package_version = binary_package_version


class FixPlanWarningPackageCannotBeInstalled(FixPlanWarning):
    fields = [
        Field("warning_type", StringDataValue),
        Field("order", IntDataValue),
        Field("data", SecurityIssueNotFixedData),
    ]

    def __init__(self, *, order: int, data: PackageCannotBeInstalledData):
        super().__init__(
            warning_type=FixWarningType.PACKAGE_CANNOT_BE_INSTALLED.value,
            order=order,
        )
        self.data = data


class FixPlanError(DataObject):
    fields = [
        Field("msg", StringDataValue),
        Field("code", StringDataValue, required=False),
    ]

    def __init__(self, *, msg: str, code: Optional[str]):
        self.msg = msg
        self.code = code


class FixPlanResult(DataObject):
    fields = [
        Field("title", StringDataValue),
        Field("expected_status", StringDataValue),
        Field("plan", data_list(FixPlanStep)),
        Field("warnings", data_list(FixPlanWarning), required=False),
        Field("error", FixPlanError, required=False),
    ]

    def __init__(
        self,
        *,
        title: str,
        expected_status: str,
        plan: List[FixPlanStep],
        warnings: List[FixPlanWarning],
        error: Optional[FixPlanError]
    ):
        self.title = title
        self.expected_status = expected_status
        self.plan = plan
        self.warnings = warnings
        self.error = error


class FixPlanUSNResult(DataObject):
    fields = [
        Field("target_usn_plan", FixPlanResult),
        Field("related_usns_plan", data_list(FixPlanResult), required=False),
    ]

    def __init__(
        self,
        *,
        target_usn_plan: FixPlanResult,
        related_usns_plan: List[FixPlanResult]
    ):
        self.target_usn_plan = target_usn_plan
        self.related_usns_plan = related_usns_plan


class FixPlan:
    def __init__(self, title: str):
        self.order = 1
        self.title = title
        self.fix_steps = []  # type: List[FixPlanStep]
        self.fix_warnings = []  # type: List[FixPlanWarning]
        self.error = None  # type: Optional[FixPlanError]

    def register_step(
        self,
        operation: FixStepType,
        data: Dict[str, Any],
    ):
        # just to make mypy happy
        fix_step = None  # type: Optional[FixPlanStep]

        if operation == FixStepType.ATTACH:
            fix_step = FixPlanAttachStep(
                order=self.order, data=AttachData.from_dict(data)
            )
        elif operation == FixStepType.ENABLE:
            fix_step = FixPlanEnableStep(
                order=self.order, data=EnableData.from_dict(data)
            )
        elif operation == FixStepType.NOOP:
            fix_step = FixPlanNoOpStep(
                order=self.order, data=NoOpData.from_dict(data)
            )
        else:
            fix_step = FixPlanAptUpgradeStep(
                order=self.order, data=AptUpgradeData.from_dict(data)
            )

        self.fix_steps.append(fix_step)
        self.order += 1

    def register_warning(
        self, warning_type: FixWarningType, data: Dict[str, Any]
    ):
        fix_warning = None  # type: Optional[FixPlanWarning]

        if warning_type == FixWarningType.SECURITY_ISSUE_NOT_FIXED:
            fix_warning = FixPlanWarningSecurityIssueNotFixed(
                order=self.order,
                data=SecurityIssueNotFixedData.from_dict(data),
            )
        else:
            fix_warning = FixPlanWarningPackageCannotBeInstalled(
                order=self.order,
                data=PackageCannotBeInstalledData.from_dict(data),
            )

        self.fix_warnings.append(fix_warning)
        self.order += 1

    def register_error(self, error_msg: str, error_code: Optional[str]):
        self.error = FixPlanError(msg=error_msg, code=error_code)

    def _get_status(self) -> str:
        if self.error:
            return "error"

        if (
            len(self.fix_steps) == 1
            and isinstance(self.fix_steps[0], FixPlanNoOpStep)
            and self.fix_steps[0].data.status == "system-not-affected"
        ):
            return str(FixStatus.SYSTEM_NOT_AFFECTED)
        elif self.fix_warnings:
            return str(FixStatus.SYSTEM_STILL_VULNERABLE)
        else:
            return str(FixStatus.SYSTEM_NON_VULNERABLE)

    @property
    def fix_plan(self):
        return FixPlanResult(
            title=self.title,
            expected_status=self._get_status(),
            plan=self.fix_steps,
            warnings=self.fix_warnings,
            error=self.error,
        )


def _get_cve_data(
    issue_id: str,
    installed_packages: Dict[str, Dict[str, str]],
    client: UASecurityClient,
) -> Tuple[Dict[str, CVEPackageStatus], Dict[str, Dict[str, Dict[str, str]]]]:
    try:
        cve = client.get_cve(cve_id=issue_id)
        usns = client.get_notices(details=issue_id)
    except exceptions.SecurityAPIError as e:
        if e.code == 404:
            raise exceptions.SecurityIssueNotFound(issue_id=issue_id)
        raise exceptions.UserFacingError(str(e))

    affected_pkg_status = get_cve_affected_source_packages_status(
        cve=cve, installed_packages=installed_packages
    )
    usn_released_pkgs = merge_usn_released_binary_package_versions(
        usns, beta_pockets={}
    )

    return affected_pkg_status, usn_released_pkgs


def _get_usn_data(
    issue_id: str,
    installed_packages: Dict[str, Dict[str, str]],
    client: UASecurityClient,
) -> Tuple[USN, List[USN]]:
    try:
        usn = client.get_notice(notice_id=issue_id)
        usns = get_related_usns(usn, client)
    except exceptions.SecurityAPIError as e:
        if e.code == 404:
            raise exceptions.SecurityIssueNotFound(issue_id=issue_id)
        raise exceptions.UserFacingError(str(e))

    if not usn.response["release_packages"]:
        # Since usn.release_packages filters to our current release only
        # check overall metadata and error if empty.
        raise exceptions.SecurityAPIMetadataError(
            "{} metadata defines no fixed package versions.".format(issue_id),
            issue_id=issue_id,
        )

    return usn, usns


def _get_upgradable_pkgs(
    binary_pkgs: List[BinaryPackageFix],
    pocket: str,
) -> Tuple[List[str], List[UnfixedPackage]]:
    upgrade_pkgs = []
    unfixed_pkgs = []

    for binary_pkg in sorted(binary_pkgs):
        check_esm_cache = pocket != UBUNTU_STANDARD_UPDATES_POCKET
        candidate_version = apt.get_pkg_candidate_version(
            binary_pkg.binary_pkg, check_esm_cache=check_esm_cache
        )
        if candidate_version and apt.compare_versions(
            binary_pkg.fixed_version, candidate_version, "le"
        ):
            upgrade_pkgs.append(binary_pkg.binary_pkg)
        else:
            unfixed_pkgs.append(
                UnfixedPackage(
                    source_package=binary_pkg.source_pkg,
                    binary_package=binary_pkg.binary_pkg,
                    version=binary_pkg.fixed_version,
                )
            )

    return upgrade_pkgs, unfixed_pkgs


def _get_upgradable_package_candidates_by_pocket(
    pkg_status_group: List[Tuple[str, CVEPackageStatus]],
    usn_released_pkgs: Dict[str, Dict[str, Dict[str, str]]],
    installed_packages: Dict[str, Dict[str, str]],
):
    binary_pocket_pkgs = defaultdict(list)
    src_pocket_pkgs = defaultdict(list)

    for src_pkg, pkg_status in pkg_status_group:
        src_pocket_pkgs[pkg_status.pocket_source].append((src_pkg, pkg_status))
        for binary_pkg, version in installed_packages[src_pkg].items():
            usn_released_src = usn_released_pkgs.get(src_pkg, {})
            if binary_pkg not in usn_released_src:
                continue
            fixed_version = usn_released_src.get(binary_pkg, {}).get(
                "version", ""
            )

            if not apt.compare_versions(fixed_version, version, "le"):
                binary_pocket_pkgs[pkg_status.pocket_source].append(
                    BinaryPackageFix(
                        source_pkg=src_pkg,
                        binary_pkg=binary_pkg,
                        fixed_version=fixed_version,
                    )
                )

    return src_pocket_pkgs, binary_pocket_pkgs


def _fix_plan_cve(issue_id: str, cfg: UAConfig) -> FixPlanResult:
    livepatch_cve_status, patch_version = _check_cve_fixed_by_livepatch(
        issue_id
    )

    if livepatch_cve_status:
        fix_plan = FixPlan(title=issue_id)
        fix_plan.register_step(
            operation=FixStepType.NOOP,
            data={"status": FixPlanNoOpStatus.FIXED_BY_LIVEPATCH.value},
        )
        return fix_plan.fix_plan

    client = UASecurityClient(cfg=cfg)
    installed_packages = query_installed_source_pkg_versions()

    try:
        affected_pkg_status, usn_released_pkgs = _get_cve_data(
            issue_id=issue_id,
            installed_packages=installed_packages,
            client=client,
        )
    except exceptions.SecurityIssueNotFound as e:
        fix_plan = FixPlan(title=issue_id)
        fix_plan.register_error(error_msg=e.msg, error_code=e.msg_code)
        return fix_plan.fix_plan

    return _generate_fix_plan(
        issue_id,
        affected_pkg_status,
        usn_released_pkgs,
        installed_packages,
        cfg,
    )


def _fix_plan_usn(issue_id: str, cfg: UAConfig) -> FixPlanUSNResult:
    client = UASecurityClient(cfg=cfg)
    installed_packages = query_installed_source_pkg_versions()

    try:
        usn, related_usns = _get_usn_data(
            issue_id=issue_id,
            installed_packages=installed_packages,
            client=client,
        )
    except exceptions.SecurityIssueNotFound as e:
        fix_plan = FixPlan(title=issue_id)
        fix_plan.register_error(error_msg=e.msg, error_code=e.msg_code)
        return FixPlanUSNResult(
            target_usn_plan=fix_plan.fix_plan,
            related_usns_plan=[],
        )

    affected_pkg_status = get_affected_packages_from_usn(
        usn=usn, installed_packages=installed_packages
    )
    usn_released_pkgs = merge_usn_released_binary_package_versions(
        [usn], beta_pockets={}
    )

    target_usn_plan = _generate_fix_plan(
        issue_id,
        affected_pkg_status,
        usn_released_pkgs,
        installed_packages,
        cfg,
    )

    related_usns_plan = []  # type: List[FixPlanResult]
    for usn in related_usns:
        affected_pkg_status = get_affected_packages_from_usn(
            usn=usn, installed_packages=installed_packages
        )
        usn_released_pkgs = merge_usn_released_binary_package_versions(
            [usn], beta_pockets={}
        )

        related_usns_plan.append(
            _generate_fix_plan(
                usn.id,
                affected_pkg_status,
                usn_released_pkgs,
                installed_packages,
                cfg,
            )
        )

    return FixPlanUSNResult(
        target_usn_plan=target_usn_plan,
        related_usns_plan=related_usns_plan,
    )


def fix_plan_cve(issue_id: str, cfg: UAConfig) -> FixPlanResult:
    if not issue_id or not re.match(CVE_OR_USN_REGEX, issue_id):
        fix_plan = FixPlan(title=issue_id)
        msg = messages.INVALID_SECURITY_ISSUE.format(issue_id=issue_id)
        fix_plan.register_error(error_msg=msg.msg, error_code=msg.name)
        return fix_plan.fix_plan

    issue_id = issue_id.upper()
    return _fix_plan_cve(issue_id, cfg)


def fix_plan_usn(issue_id: str, cfg: UAConfig) -> FixPlanUSNResult:
    if not issue_id or not re.match(CVE_OR_USN_REGEX, issue_id):
        fix_plan = FixPlan(title=issue_id)
        msg = messages.INVALID_SECURITY_ISSUE.format(issue_id=issue_id)
        fix_plan.register_error(error_msg=msg.msg, error_code=msg.name)
        return FixPlanUSNResult(
            target_usn_plan=fix_plan.fix_plan,
            related_usns_plan=[],
        )

    issue_id = issue_id.upper()
    return _fix_plan_usn(issue_id, cfg)


def _generate_fix_plan(
    issue_id: str,
    affected_pkg_status: Dict[str, CVEPackageStatus],
    usn_released_pkgs: Dict[str, Dict[str, Dict[str, str]]],
    installed_pkgs: Dict[str, Dict[str, str]],
    cfg: UAConfig,
) -> FixPlanResult:
    fix_plan = FixPlan(title=issue_id)

    count = len(affected_pkg_status)
    if count == 0:
        fix_plan.register_step(
            operation=FixStepType.NOOP,
            data={"status": FixPlanNoOpStatus.NOT_AFFECTED.value},
        )
        return fix_plan.fix_plan

    pkg_status_groups = group_by_usn_package_status(
        affected_pkg_status, usn_released_pkgs
    )

    for status_value, pkg_status_group in sorted(pkg_status_groups.items()):
        if status_value != "released":
            fix_plan.register_warning(
                warning_type=FixWarningType.SECURITY_ISSUE_NOT_FIXED,
                data={
                    "source_packages": [
                        src_pkg for src_pkg, _ in pkg_status_group
                    ],
                    "status": status_value,
                },
            )
        else:
            (
                src_pocket_pkgs,
                binary_pocket_pkgs,
            ) = _get_upgradable_package_candidates_by_pocket(
                pkg_status_group,
                usn_released_pkgs,
                installed_pkgs,
            )

    if not src_pocket_pkgs:
        return fix_plan.fix_plan

    all_already_installed = True
    for pocket in [
        UBUNTU_STANDARD_UPDATES_POCKET,
        UA_INFRA_POCKET,
        UA_APPS_POCKET,
    ]:
        pkg_src_group = src_pocket_pkgs[pocket]
        binary_pkgs = binary_pocket_pkgs[pocket]

        if not binary_pkgs:
            continue
        else:
            all_already_installed = False

        upgrade_pkgs, unfixed_pkgs = _get_upgradable_pkgs(binary_pkgs, pocket)

        if unfixed_pkgs:
            for unfixed_pkg in unfixed_pkgs:
                fix_plan.register_warning(
                    warning_type=FixWarningType.PACKAGE_CANNOT_BE_INSTALLED,
                    data={
                        "binary_package": unfixed_pkg.binary_package,
                        "binary_package_version": unfixed_pkg.version,
                        "source_package": unfixed_pkg.source_package,
                    },
                )

        if pocket != UBUNTU_STANDARD_UPDATES_POCKET:
            if not _is_attached(cfg).is_attached:
                fix_plan.register_step(
                    operation=FixStepType.ATTACH,
                    data={"reason": "required-pro-service"},
                )
            else:
                contract_expiry_status, _ = get_contract_expiry_status(cfg)
                if contract_expiry_status != ContractExpiryStatus.ACTIVE:
                    fix_plan.register_step(
                        operation=FixStepType.ATTACH,
                        data={
                            "reason": FixPlanAttachReason.EXPIRED_CONTRACT.value  # noqa
                        },
                    )

            enabled_services = _enabled_services(cfg).enabled_services or []
            if pocket == UA_INFRA_POCKET:
                service_to_check = "esm-infra"
            else:
                service_to_check = "esm-apps"

            if service_to_check not in enabled_services:
                fix_plan.register_step(
                    operation=FixStepType.ENABLE,
                    data={
                        "service": service_to_check,
                    },
                )

        fix_plan.register_step(
            operation=FixStepType.APT_UPGRADE,
            data={
                "binary_packages": upgrade_pkgs,
                "source_packages": [src_pkg for src_pkg, _ in pkg_src_group],
            },
        )

    if all_already_installed:
        fix_plan.register_step(
            operation=FixStepType.NOOP,
            data={"status": FixPlanNoOpStatus.ALREADY_FIXED.value},
        )

    return fix_plan.fix_plan
