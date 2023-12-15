import enum
import re
from collections import defaultdict
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from uaclient import apt, exceptions, messages
from uaclient.api.u.pro.security.fix._common import (
    CVE,
    CVE_OR_USN_REGEX,
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
from uaclient.api.u.pro.status.enabled_services.v1 import _enabled_services
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.config import UAConfig
from uaclient.contract import ContractExpiryStatus, get_contract_expiry_status
from uaclient.data_types import (
    DataObject,
    Field,
    IntDataValue,
    StringDataValue,
    data_list,
)

STANDARD_UPDATES_POCKET = "standard-updates"
ESM_INFRA_POCKET = "esm-infra"
ESM_APPS_POCKET = "esm-apps"

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
        Field("pocket", StringDataValue),
    ]

    def __init__(
        self,
        *,
        binary_packages: List[str],
        source_packages: List[str],
        pocket: str
    ):
        self.binary_packages = binary_packages
        self.source_packages = source_packages
        self.pocket = pocket


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
        Field("required_service", StringDataValue),
        Field("source_packages", data_list(StringDataValue)),
    ]

    def __init__(
        self, *, reason: str, source_packages: List[str], required_service: str
    ):
        self.reason = reason
        self.source_packages = source_packages
        self.required_service = required_service


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
        Field("source_packages", data_list(StringDataValue)),
    ]

    def __init__(self, *, service: str, source_packages: List[str]):
        self.service = service
        self.source_packages = source_packages


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


class NoOpLivepatchFixData(NoOpData):
    fields = [
        Field("status", StringDataValue),
        Field("patch_version", StringDataValue),
    ]

    def __init__(self, *, status: str, patch_version: str):
        super().__init__(status=status)
        self.patch_version = patch_version


class FixPlanNoOpLivepatchFixStep(FixPlanNoOpStep):
    fields = [
        Field("operation", StringDataValue),
        Field("data", NoOpLivepatchFixData),
        Field("order", IntDataValue),
    ]

    def __init__(self, *, data: NoOpLivepatchFixData, order: int):
        super().__init__(data=data, order=order)


class NoOpAlreadyFixedData(NoOpData):
    fields = [
        Field("status", StringDataValue),
        Field("source_packages", data_list(StringDataValue)),
        Field("pocket", StringDataValue),
    ]

    def __init__(
        self, *, status: str, source_packages: List[str], pocket: str
    ):
        super().__init__(status=status)
        self.source_packages = source_packages
        self.pocket = pocket


class FixPlanNoOpAlreadyFixedStep(FixPlanNoOpStep):
    fields = [
        Field("operation", StringDataValue),
        Field("data", NoOpLivepatchFixData),
        Field("order", IntDataValue),
    ]

    def __init__(self, *, data: NoOpAlreadyFixedData, order: int):
        super().__init__(data=data, order=order)


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
        Field("related_source_packages", data_list(StringDataValue)),
        Field("pocket", StringDataValue),
    ]

    def __init__(
        self,
        *,
        binary_package: str,
        binary_package_version: str,
        source_package: str,
        pocket: str,
        related_source_packages: List[str]
    ):
        self.source_package = source_package
        self.binary_package = binary_package
        self.binary_package_version = binary_package_version
        self.pocket = pocket
        self.related_source_packages = related_source_packages


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


class AdditionalData(DataObject):
    pass


class USNAdditionalData(AdditionalData):

    fields = [
        Field("associated_cves", data_list(StringDataValue)),
        Field("associated_launchpad_bugs", data_list(StringDataValue)),
    ]

    def __init__(
        self,
        *,
        associated_cves: List[str],
        associated_launchpad_bugs: List[str]
    ):
        self.associated_cves = associated_cves
        self.associated_launchpad_bugs = associated_launchpad_bugs


class FixPlanResult(DataObject):
    fields = [
        Field("title", StringDataValue),
        Field("description", StringDataValue, required=False),
        Field("expected_status", StringDataValue),
        Field("affected_packages", data_list(StringDataValue), required=False),
        Field("plan", data_list(FixPlanStep)),
        Field("warnings", data_list(FixPlanWarning), required=False),
        Field("error", FixPlanError, required=False),
        Field("additional_data", AdditionalData, required=False),
    ]

    def __init__(
        self,
        *,
        title: str,
        expected_status: str,
        plan: List[FixPlanStep],
        warnings: List[FixPlanWarning],
        error: Optional[FixPlanError],
        additional_data: AdditionalData,
        description: Optional[str] = None,
        affected_packages: Optional[List[str]] = None
    ):
        self.title = title
        self.description = description
        self.expected_status = expected_status
        self.affected_packages = affected_packages
        self.plan = plan
        self.warnings = warnings
        self.error = error
        self.additional_data = additional_data


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
    def __init__(
        self,
        title: str,
        description: Optional[str],
        affected_packages: Optional[List[str]] = None,
    ):
        self.order = 1
        self.title = title
        self.description = description
        self.affected_packages = affected_packages
        self.fix_steps = []  # type: List[FixPlanStep]
        self.fix_warnings = []  # type: List[FixPlanWarning]
        self.error = None  # type: Optional[FixPlanError]
        self.additional_data = AdditionalData()

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
            if "patch_version" in data:
                fix_step = FixPlanNoOpLivepatchFixStep(
                    order=self.order, data=NoOpLivepatchFixData.from_dict(data)
                )
            elif "source_packages" in data:
                fix_step = FixPlanNoOpAlreadyFixedStep(
                    order=self.order, data=NoOpAlreadyFixedData.from_dict(data)
                )
            else:
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

    def register_additional_data(self, additional_data: Dict[str, Any]):
        self.additional_data = AdditionalData(**additional_data)

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
            description=self.description,
            expected_status=self._get_status(),
            affected_packages=self.affected_packages,
            plan=self.fix_steps,
            warnings=self.fix_warnings,
            error=self.error,
            additional_data=self.additional_data,
        )


class USNFixPlan(FixPlan):
    def register_additional_data(self, additional_data: Dict[str, Any]):
        self.additional_data = USNAdditionalData(**additional_data)


def get_fix_plan(
    title: str,
    description: Optional[str] = None,
    affected_packages: Optional[List[str]] = None,
):
    if not title or "cve" in title.lower():
        return FixPlan(
            title=title,
            description=description,
            affected_packages=affected_packages,
        )

    return USNFixPlan(
        title=title,
        description=description,
        affected_packages=affected_packages,
    )


def _get_cve_data(
    issue_id: str,
    client: UASecurityClient,
) -> Tuple[CVE, List[USN]]:
    try:
        cve = client.get_cve(cve_id=issue_id)
        usns = client.get_notices(details=issue_id)
    except exceptions.SecurityAPIError as e:
        if e.code == 404:
            raise exceptions.SecurityIssueNotFound(issue_id=issue_id)
        raise e

    return cve, usns


def _get_usn_data(
    issue_id: str, client: UASecurityClient
) -> Tuple[USN, List[USN]]:
    try:
        usn = client.get_notice(notice_id=issue_id)
        usns = get_related_usns(usn, client)
    except exceptions.SecurityAPIError as e:
        if e.code == 404:
            raise exceptions.SecurityIssueNotFound(issue_id=issue_id)
        raise e

    if not usn.response["release_packages"]:
        # Since usn.release_packages filters to our current release only
        # check overall metadata and error if empty.
        raise exceptions.SecurityAPIMetadataError(
            error_msg="metadata defines no fixed package versions.",
            issue=issue_id,
            extra_info="",
        )

    return usn, usns


def _get_upgradable_pkgs(
    binary_pkgs: List[BinaryPackageFix],
    pocket: str,
) -> Tuple[List[str], List[UnfixedPackage]]:
    upgrade_pkgs = []
    unfixed_pkgs = []

    for binary_pkg in sorted(binary_pkgs):
        check_esm_cache = (
            pocket != messages.SECURITY_UBUNTU_STANDARD_UPDATES_POCKET
        )
        candidate_version = apt.get_pkg_candidate_version(
            binary_pkg.binary_pkg, check_esm_cache=check_esm_cache
        )
        if (
            candidate_version
            and apt.version_compare(
                binary_pkg.fixed_version, candidate_version
            )
            <= 0
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
    installed_pkgs: Dict[str, Dict[str, str]],
):
    binary_pocket_pkgs = defaultdict(list)
    src_pocket_pkgs = defaultdict(list)

    for src_pkg, pkg_status in pkg_status_group:
        src_pocket_pkgs[pkg_status.pocket_source].append((src_pkg, pkg_status))
        for binary_pkg, version in installed_pkgs[src_pkg].items():
            usn_released_src = usn_released_pkgs.get(src_pkg, {})
            if binary_pkg not in usn_released_src:
                continue
            fixed_version = usn_released_src.get(binary_pkg, {}).get(
                "version", ""
            )

            if apt.version_compare(fixed_version, version) > 0:
                binary_pocket_pkgs[pkg_status.pocket_source].append(
                    BinaryPackageFix(
                        source_pkg=src_pkg,
                        binary_pkg=binary_pkg,
                        fixed_version=fixed_version,
                    )
                )

    return src_pocket_pkgs, binary_pocket_pkgs


def _get_cve_description(
    cve: CVE,
    installed_pkgs: Dict[str, Dict[str, str]],
):
    if not cve.notices:
        return cve.description

    for notice in cve.notices:
        usn_pkgs = notice.release_packages.keys()
        for pkg in usn_pkgs:
            if pkg in installed_pkgs:
                return notice.title

    return cve.notices[0].title


def _fix_plan_cve(issue_id: str, cfg: UAConfig) -> FixPlanResult:
    livepatch_cve_status, patch_version = _check_cve_fixed_by_livepatch(
        issue_id
    )

    if livepatch_cve_status:
        fix_plan = get_fix_plan(title=issue_id)
        fix_plan.register_step(
            operation=FixStepType.NOOP,
            data={
                "status": FixPlanNoOpStatus.FIXED_BY_LIVEPATCH.value,
                "patch_version": patch_version,
            },
        )
        return fix_plan.fix_plan

    client = UASecurityClient(cfg=cfg)
    installed_pkgs = query_installed_source_pkg_versions()

    try:
        cve, usns = _get_cve_data(issue_id=issue_id, client=client)
    except (
        exceptions.SecurityIssueNotFound,
        exceptions.SecurityAPIError,
    ) as e:
        fix_plan = get_fix_plan(title=issue_id)
        fix_plan.register_error(error_msg=e.msg, error_code=e.msg_code)
        return fix_plan.fix_plan

    affected_pkg_status = get_cve_affected_source_packages_status(
        cve=cve, installed_packages=installed_pkgs
    )
    usn_released_pkgs = merge_usn_released_binary_package_versions(
        usns, beta_pockets={}
    )

    cve_description = _get_cve_description(cve, installed_pkgs)

    return _generate_fix_plan(
        issue_id=issue_id,
        issue_description=cve_description,
        affected_pkg_status=affected_pkg_status,
        usn_released_pkgs=usn_released_pkgs,
        installed_pkgs=installed_pkgs,
        cfg=cfg,
    )


def _fix_plan_usn(issue_id: str, cfg: UAConfig) -> FixPlanUSNResult:
    client = UASecurityClient(cfg=cfg)
    installed_pkgs = query_installed_source_pkg_versions()

    try:
        usn, related_usns = _get_usn_data(issue_id=issue_id, client=client)
    except (
        exceptions.SecurityIssueNotFound,
        exceptions.SecurityAPIError,
    ) as e:
        fix_plan = get_fix_plan(title=issue_id)
        fix_plan.register_error(error_msg=e.msg, error_code=e.msg_code)
        return FixPlanUSNResult(
            target_usn_plan=fix_plan.fix_plan,
            related_usns_plan=[],
        )

    affected_pkg_status = get_affected_packages_from_usn(
        usn=usn, installed_packages=installed_pkgs
    )
    usn_released_pkgs = merge_usn_released_binary_package_versions(
        [usn], beta_pockets={}
    )
    additional_data = {
        "associated_cves": [] if not usn.cves_ids else usn.cves_ids,
        "associated_launchpad_bugs": []
        if not usn.references
        else usn.references,
    }

    target_usn_plan = _generate_fix_plan(
        issue_id=issue_id,
        issue_description=usn.title,
        affected_pkg_status=affected_pkg_status,
        usn_released_pkgs=usn_released_pkgs,
        installed_pkgs=installed_pkgs,
        cfg=cfg,
        additional_data=additional_data,
    )

    related_usns_plan = []  # type: List[FixPlanResult]
    for usn in related_usns:
        affected_pkg_status = get_affected_packages_from_usn(
            usn=usn, installed_packages=installed_pkgs
        )
        usn_released_pkgs = merge_usn_released_binary_package_versions(
            [usn], beta_pockets={}
        )
        additional_data = {
            "associated_cves": [] if not usn.cves_ids else usn.cves_ids,
            "associated_launchpad_bugs": []
            if not usn.references
            else usn.references,
        }

        related_usns_plan.append(
            _generate_fix_plan(
                issue_id=usn.id,
                issue_description=usn.title,
                affected_pkg_status=affected_pkg_status,
                usn_released_pkgs=usn_released_pkgs,
                installed_pkgs=installed_pkgs,
                cfg=cfg,
                additional_data=additional_data,
            )
        )

    return FixPlanUSNResult(
        target_usn_plan=target_usn_plan,
        related_usns_plan=related_usns_plan,
    )


def fix_plan_cve(issue_id: str, cfg: UAConfig) -> FixPlanResult:
    if not issue_id or not re.match(CVE_OR_USN_REGEX, issue_id):
        fix_plan = get_fix_plan(title=issue_id)
        msg = messages.INVALID_SECURITY_ISSUE.format(issue_id=issue_id)
        fix_plan.register_error(error_msg=msg.msg, error_code=msg.name)
        return fix_plan.fix_plan

    issue_id = issue_id.upper()
    return _fix_plan_cve(issue_id, cfg)


def fix_plan_usn(issue_id: str, cfg: UAConfig) -> FixPlanUSNResult:
    if not issue_id or not re.match(CVE_OR_USN_REGEX, issue_id):
        fix_plan = get_fix_plan(title=issue_id)
        msg = messages.INVALID_SECURITY_ISSUE.format(issue_id=issue_id)
        fix_plan.register_error(error_msg=msg.msg, error_code=msg.name)
        return FixPlanUSNResult(
            target_usn_plan=fix_plan.fix_plan,
            related_usns_plan=[],
        )

    issue_id = issue_id.upper()
    return _fix_plan_usn(issue_id, cfg)


def get_pocket_short_name(pocket: str):
    if pocket == messages.SECURITY_UBUNTU_STANDARD_UPDATES_POCKET:
        return STANDARD_UPDATES_POCKET
    elif pocket == messages.SECURITY_UA_INFRA_POCKET:
        return ESM_INFRA_POCKET
    elif pocket == messages.SECURITY_UA_APPS_POCKET:
        return ESM_APPS_POCKET
    else:
        return pocket


def _generate_fix_plan(
    *,
    issue_id: str,
    issue_description: str,
    affected_pkg_status: Dict[str, CVEPackageStatus],
    usn_released_pkgs: Dict[str, Dict[str, Dict[str, str]]],
    installed_pkgs: Dict[str, Dict[str, str]],
    cfg: UAConfig,
    additional_data=None
) -> FixPlanResult:
    count = len(affected_pkg_status)
    src_pocket_pkgs = defaultdict(list)

    fix_plan = get_fix_plan(
        title=issue_id,
        description=issue_description,
        affected_packages=sorted(list(affected_pkg_status.keys())),
    )

    if additional_data:
        fix_plan.register_additional_data(additional_data)

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

    for pocket in [
        messages.SECURITY_UBUNTU_STANDARD_UPDATES_POCKET,
        messages.SECURITY_UA_INFRA_POCKET,
        messages.SECURITY_UA_APPS_POCKET,
    ]:
        pkg_src_group = src_pocket_pkgs[pocket]
        binary_pkgs = binary_pocket_pkgs[pocket]
        source_pkgs = [src_pkg for src_pkg, _ in pkg_src_group]
        pocket_name = get_pocket_short_name(pocket)

        if not binary_pkgs:
            if source_pkgs:
                fix_plan.register_step(
                    operation=FixStepType.NOOP,
                    data={
                        "status": FixPlanNoOpStatus.ALREADY_FIXED.value,
                        "source_packages": source_pkgs,
                        "pocket": pocket_name,
                    },
                )
            continue

        upgrade_pkgs, unfixed_pkgs = _get_upgradable_pkgs(binary_pkgs, pocket)

        if unfixed_pkgs:
            for unfixed_pkg in unfixed_pkgs:
                fix_plan.register_warning(
                    warning_type=FixWarningType.PACKAGE_CANNOT_BE_INSTALLED,
                    data={
                        "binary_package": unfixed_pkg.binary_package,
                        "binary_package_version": unfixed_pkg.version,
                        "source_package": unfixed_pkg.source_package,
                        "related_source_packages": source_pkgs,
                        "pocket": pocket_name,
                    },
                )

        if pocket != messages.SECURITY_UBUNTU_STANDARD_UPDATES_POCKET:
            if pocket == messages.SECURITY_UA_INFRA_POCKET:
                service_to_check = "esm-infra"
            else:
                service_to_check = "esm-apps"

            if not _is_attached(cfg).is_attached:
                fix_plan.register_step(
                    operation=FixStepType.ATTACH,
                    data={
                        "reason": "required-pro-service",
                        "source_packages": source_pkgs,
                        "required_service": service_to_check,
                    },
                )
            else:
                contract_expiry_status, _ = get_contract_expiry_status(cfg)
                if contract_expiry_status != ContractExpiryStatus.ACTIVE:
                    fix_plan.register_step(
                        operation=FixStepType.ATTACH,
                        data={
                            "reason": FixPlanAttachReason.EXPIRED_CONTRACT.value,  # noqa
                            "source_packages": source_pkgs,
                        },
                    )

            enabled_services = _enabled_services(cfg).enabled_services or []
            enabled_services_names = (
                [service.name for service in enabled_services]
                if enabled_services
                else []
            )
            if service_to_check not in enabled_services_names:
                fix_plan.register_step(
                    operation=FixStepType.ENABLE,
                    data={
                        "service": service_to_check,
                        "source_packages": source_pkgs,
                    },
                )

        fix_plan.register_step(
            operation=FixStepType.APT_UPGRADE,
            data={
                "binary_packages": upgrade_pkgs,
                "source_packages": source_pkgs,
                "pocket": pocket_name,
            },
        )

    return fix_plan.fix_plan
