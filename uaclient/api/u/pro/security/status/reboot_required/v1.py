from typing import List, Optional

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
from uaclient.livepatch import status
from uaclient.security_status import (
    get_reboot_required_pkgs,
    get_reboot_status,
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


def reboot_required() -> RebootRequiredResult:
    return _reboot_required(UAConfig())


def _reboot_required(cfg: UAConfig) -> RebootRequiredResult:
    reboot_status = get_reboot_status()
    reboot_required_pkgs = get_reboot_required_pkgs()
    livepatch_status = status()

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
