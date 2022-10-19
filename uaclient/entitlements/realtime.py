from typing import Optional, Tuple  # noqa: F401

from uaclient import event_logger, messages, system, util
from uaclient.entitlements import repo
from uaclient.entitlements.base import IncompatibleService
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
