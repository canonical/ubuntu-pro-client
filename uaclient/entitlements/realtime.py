from typing import Any, Dict, Optional, Tuple, Type  # noqa: F401

from uaclient import apt, event_logger, messages, system, util
from uaclient.entitlements import repo
from uaclient.entitlements.base import IncompatibleService, UAEntitlement
from uaclient.types import (  # noqa: F401
    MessagingOperations,
    MessagingOperationsDict,
    StaticAffordance,
)

event = event_logger.get_event_logger()


class RealtimeKernelEntitlement(repo.RepoEntitlement):
    name = "realtime-kernel"
    title = messages.REALTIME_TITLE
    description = messages.REALTIME_DESCRIPTION
    help_text = messages.REALTIME_HELP_TEXT
    help_doc_url = messages.urls.REALTIME_HOME_PAGE
    repo_key_file = "ubuntu-pro-realtime-kernel.gpg"
    apt_noninteractive = True
    supports_access_only = True
    supports_purge = False
    origin = "UbuntuRealtimeKernel"

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
            RaspberryPiRealtime.variant_name: RaspberryPiRealtime,
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

        pre_disable = None  # type: Optional[MessagingOperations]
        if not self.purge:
            pre_disable = [
                (
                    util.prompt_for_confirmation,
                    {
                        "msg": messages.REALTIME_PRE_DISABLE_PROMPT,
                        "assume_yes": self.assume_yes,
                    },
                )
            ]

        return {
            "pre_enable": pre_enable,
            "pre_disable": pre_disable,
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


class RealtimeVariant(RealtimeKernelEntitlement):
    @property
    def incompatible_services(self) -> Tuple[IncompatibleService, ...]:
        incompatible_variants = tuple(
            [
                IncompatibleService(
                    cls,
                    messages.REALTIME_VARIANT_INCOMPATIBLE.format(
                        service=self.title, variant=cls.title
                    ),
                )
                for name, cls in self.other_variants.items()
            ]
        )
        return super().incompatible_services + incompatible_variants


class GenericRealtime(RealtimeVariant):
    variant_name = "generic"
    title = messages.REALTIME_GENERIC_TITLE
    description = messages.REALTIME_GENERIC_DESCRIPTION
    is_variant = True
    check_packages_are_installed = True


class NvidiaTegraRealtime(RealtimeVariant):
    variant_name = "nvidia-tegra"
    title = messages.REALTIME_NVIDIA_TITLE
    description = messages.REALTIME_NVIDIA_DESCRIPTION
    is_variant = True
    check_packages_are_installed = True


class RaspberryPiRealtime(RealtimeVariant):
    variant_name = "rpi"
    title = messages.REALTIME_RASPI_TITLE
    description = messages.REALTIME_RASPI_DESCRIPTION
    is_variant = True
    check_packages_are_installed = True


class IntelIotgRealtime(RealtimeVariant):
    variant_name = "intel-iotg"
    title = messages.REALTIME_INTEL_TITLE
    description = messages.REALTIME_INTEL_DESCRIPTION
    is_variant = True
    check_packages_are_installed = True

    def verify_platform_checks(
        self, platform_checks: Dict[str, Any]
    ) -> Tuple[bool, Optional[messages.NamedMessage]]:
        vendor_id = system.get_cpu_info().vendor_id
        cpu_vendor_ids = platform_checks.get("cpu_vendor_ids", [])
        if vendor_id in cpu_vendor_ids:
            return True, None
        else:
            return False, messages.INAPPLICABLE_VENDOR_NAME.format(
                title=self.title,
                vendor=vendor_id,
                supported_vendors=",".join(cpu_vendor_ids),
            )
