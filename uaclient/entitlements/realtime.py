from typing import Dict, Optional, Tuple, Type  # noqa: F401

from uaclient import apt, event_logger, messages, system, util
from uaclient.entitlements import repo
from uaclient.entitlements.base import IncompatibleService, UAEntitlement
from uaclient.types import (  # noqa: F401
    MessagingOperations,
    MessagingOperationsDict,
    StaticAffordance,
)

event = event_logger.get_event_logger()

REALTIME_KERNEL_DOCS_URL = "https://ubuntu.com/realtime-kernel"


class RealtimeKernelEntitlement(repo.RepoEntitlement):
    name = "realtime-kernel"
    title = "Real-time kernel"
    description = "Ubuntu kernel with PREEMPT_RT patches integrated"
    help_doc_url = REALTIME_KERNEL_DOCS_URL
    repo_key_file = "ubuntu-advantage-realtime-kernel.gpg"
    apt_noninteractive = True
    supports_access_only = True

    def _check_for_reboot(self) -> bool:
        """Check if system needs to be rebooted."""
        reboot_required = system.should_reboot(
            installed_pkgs=set(self.packages),
            installed_pkgs_regex=set(["linux-.*-realtime"]),
        )
        event.needs_reboot(reboot_required)
        return reboot_required

    def _get_variants(self) -> Dict[str, Type[UAEntitlement]]:
        return {
            GenericRealtime.variant_name: GenericRealtime,
            NvidiaTegraRealtime.variant_name: NvidiaTegraRealtime,
            IntelIotgRealtime.variant_name: IntelIotgRealtime,
        }

    @property
    def incompatible_services(self) -> Tuple[IncompatibleService, ...]:
        from uaclient.entitlements.fips import (
            FIPSEntitlement,
            FIPSUpdatesEntitlement,
        )
        from uaclient.entitlements.livepatch import LivepatchEntitlement

        return (
            IncompatibleService(
                FIPSEntitlement, messages.REALTIME_FIPS_INCOMPATIBLE
            ),
            IncompatibleService(
                FIPSUpdatesEntitlement,
                messages.REALTIME_FIPS_UPDATES_INCOMPATIBLE,
            ),
            IncompatibleService(
                LivepatchEntitlement, messages.REALTIME_LIVEPATCH_INCOMPATIBLE
            ),
        )

    @property
    def static_affordances(self) -> Tuple[StaticAffordance, ...]:
        return (
            (
                messages.REALTIME_ERROR_INSTALL_ON_CONTAINER,
                lambda: system.is_container(),
                False,
            ),
        )

    @property
    def messaging(
        self,
    ) -> MessagingOperationsDict:
        pre_enable = None  # type: Optional[MessagingOperations]
        if not self.access_only:
            pre_enable = [
                (
                    util.prompt_for_confirmation,
                    {
                        "msg": messages.REALTIME_PROMPT,
                        "assume_yes": self.assume_yes,
                        "default": True,
                    },
                )
            ]
        return {
            "pre_enable": pre_enable,
            "pre_disable": [
                (
                    util.prompt_for_confirmation,
                    {
                        "msg": messages.REALTIME_PRE_DISABLE_PROMPT,
                        "assume_yes": self.assume_yes,
                    },
                )
            ],
        }

    def remove_packages(self) -> None:
        packages = set(self.packages).intersection(
            set(apt.get_installed_packages_names())
        )
        if packages:
            apt.remove_packages(
                list(packages),
                messages.DISABLE_FAILED_TMPL.format(title=self.title),
            )


class GenericRealtime(RealtimeKernelEntitlement):
    variant_name = "generic"
    title = "Real-time kernel"
    description = "Generic version of the RT kernel (default)"
    is_variant = True
    check_packages_are_installed = True

    @property
    def incompatible_services(self) -> Tuple[IncompatibleService, ...]:
        return (
            IncompatibleService(
                NvidiaTegraRealtime,
                messages.REALTIME_VARIANT_INCOMPATIBLE.format(
                    service=self.title, variant=NvidiaTegraRealtime.title
                ),
            ),
            IncompatibleService(
                IntelIotgRealtime,
                messages.REALTIME_VARIANT_INCOMPATIBLE.format(
                    service=self.title, variant=IntelIotgRealtime.title
                ),
            ),
        )


class NvidiaTegraRealtime(RealtimeKernelEntitlement):
    variant_name = "nvidia-tegra"
    title = "Real-time Nvidia Tegra Kernel"
    description = "RT kernel optimized for NVidia Tegra platforms"
    selector_key = "platform"
    is_variant = True
    check_packages_are_installed = True

    @property
    def messaging(
        self,
    ) -> MessagingOperationsDict:
        return {}

    @property
    def incompatible_services(self) -> Tuple[IncompatibleService, ...]:
        return (
            IncompatibleService(
                GenericRealtime,
                messages.REALTIME_VARIANT_INCOMPATIBLE.format(
                    service=self.title, variant=GenericRealtime.title
                ),
            ),
            IncompatibleService(
                IntelIotgRealtime,
                messages.REALTIME_VARIANT_INCOMPATIBLE.format(
                    service=self.title, variant=IntelIotgRealtime.title
                ),
            ),
        )


class IntelIotgRealtime(RealtimeKernelEntitlement):
    variant_name = "intel-iotg"
    title = "Real-time Intel IOTG Kernel"
    description = "RT kernel optimized for Intel IOTG platform"
    selector_key = "platform"
    is_variant = True
    check_packages_are_installed = True

    @property
    def messaging(
        self,
    ) -> MessagingOperationsDict:
        return {}

    @property
    def incompatible_services(self) -> Tuple[IncompatibleService, ...]:
        return (
            IncompatibleService(
                NvidiaTegraRealtime,
                messages.REALTIME_VARIANT_INCOMPATIBLE.format(
                    service=self.title, variant=NvidiaTegraRealtime.title
                ),
            ),
            IncompatibleService(
                GenericRealtime,
                messages.REALTIME_VARIANT_INCOMPATIBLE.format(
                    service=self.title, variant=GenericRealtime.title
                ),
            ),
        )
