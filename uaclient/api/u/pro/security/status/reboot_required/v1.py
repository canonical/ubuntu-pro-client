from enum import Enum
from typing import List, Optional

from uaclient import exceptions, livepatch
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UAConfig
from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    Field,
    StringDataValue,
    data_list,
)
from uaclient.system import (
    get_kernel_info,
    get_reboot_required_pkgs,
    should_reboot,
)


class RebootRequiredPkgs(DataObject):
    fields = [
        Field("standard_packages", data_list(StringDataValue), False),
        Field("kernel_packages", data_list(StringDataValue), False),
    ]

    def __init__(
        self,
        standard_packages: Optional[List[str]],
        kernel_packages: Optional[List[str]],
    ):
        self.standard_packages = standard_packages
        self.kernel_packages = kernel_packages


class RebootRequiredResult(DataObject, AdditionalInfo):
    fields = [
        Field("reboot_required", StringDataValue),
        Field("reboot_required_packages", RebootRequiredPkgs),
        Field("livepatch_enabled_and_kernel_patched", BoolDataValue),
        Field("livepatch_enabled", BoolDataValue),
        Field("livepatch_state", StringDataValue, False),
        Field("livepatch_support", StringDataValue, False),
    ]

    def __init__(
        self,
        reboot_required: str,
        reboot_required_packages: RebootRequiredPkgs,
        livepatch_enabled_and_kernel_patched: bool,
        livepatch_enabled: bool,
        livepatch_state: Optional[str],
        livepatch_support: Optional[str],
    ):
        self.reboot_required = reboot_required
        self.reboot_required_packages = reboot_required_packages
        self.livepatch_enabled_and_kernel_patched = (
            livepatch_enabled_and_kernel_patched
        )
        self.livepatch_enabled = livepatch_enabled
        self.livepatch_state = livepatch_state
        self.livepatch_support = livepatch_support


class RebootStatus(Enum):
    REBOOT_REQUIRED = "yes"
    REBOOT_NOT_REQUIRED = "no"
    REBOOT_REQUIRED_LIVEPATCH_APPLIED = "yes-kernel-livepatches-applied"


def _get_reboot_status():
    if not should_reboot():
        return RebootStatus.REBOOT_NOT_REQUIRED

    reboot_required_pkgs = get_reboot_required_pkgs()

    if not reboot_required_pkgs:
        return RebootStatus.REBOOT_REQUIRED

    # We will only check the Livepatch state if all the
    # packages that require a reboot are kernel related
    if reboot_required_pkgs.standard_packages:
        return RebootStatus.REBOOT_REQUIRED

    # If there are no kernel packages to cover or livepatch is not installed,
    # we should only return that a reboot is required
    if (
        not reboot_required_pkgs.kernel_packages
        or not livepatch.is_livepatch_installed()
    ):
        return RebootStatus.REBOOT_REQUIRED

    our_kernel_version = get_kernel_info().proc_version_signature_version

    try:
        lp_status = livepatch.status()
    except exceptions.ProcessExecutionError:
        return RebootStatus.REBOOT_REQUIRED

    if (
        lp_status is not None
        and our_kernel_version is not None
        and our_kernel_version == lp_status.kernel
        and lp_status.livepatch is not None
        and (
            lp_status.livepatch.state == "applied"
            or lp_status.livepatch.state == "nothing-to-apply"
        )
        and lp_status.supported == "supported"
    ):
        return RebootStatus.REBOOT_REQUIRED_LIVEPATCH_APPLIED

    # Any other Livepatch status will not be considered here to modify the
    # reboot state
    return RebootStatus.REBOOT_REQUIRED


def reboot_required() -> RebootRequiredResult:
    return _reboot_required(UAConfig())


def _reboot_required(cfg: UAConfig) -> RebootRequiredResult:
    reboot_status = _get_reboot_status()
    reboot_required_pkgs = get_reboot_required_pkgs()
    livepatch_status = livepatch.status()

    if not livepatch_status:
        livepatch_enabled_and_kernel_patched = False
        livepatch_enabled = False
        livepatch_state = None
        livepatch_support = None
    else:
        livepatch_enabled = True
        livepatch_support = livepatch_status.supported
        livepatch_state = (
            livepatch_status.livepatch.state
            if livepatch_status.livepatch
            else None
        )
        if (
            livepatch_state not in ("applied", "nothing-to-apply")
            and livepatch_support != "supported"
        ):
            livepatch_enabled_and_kernel_patched = False
        else:
            livepatch_enabled_and_kernel_patched = True

    return RebootRequiredResult(
        reboot_required=reboot_status.value,
        reboot_required_packages=RebootRequiredPkgs(
            standard_packages=reboot_required_pkgs.standard_packages
            if reboot_required_pkgs
            else None,
            kernel_packages=reboot_required_pkgs.kernel_packages
            if reboot_required_pkgs
            else None,
        ),
        livepatch_enabled_and_kernel_patched=livepatch_enabled_and_kernel_patched,  # noqa
        livepatch_enabled=livepatch_enabled,
        livepatch_state=livepatch_state,
        livepatch_support=livepatch_support,
    )


endpoint = APIEndpoint(
    version="v1",
    name="RebootRequired",
    fn=_reboot_required,
    options_cls=None,
)
