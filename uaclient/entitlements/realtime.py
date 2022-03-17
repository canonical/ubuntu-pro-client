from typing import Tuple

from uaclient import messages
from uaclient.entitlements import repo
from uaclient.entitlements.base import IncompatibleService
from uaclient.types import MessagingOperationsDict

REALTIME_KERNEL_DOCS_URL = "https://ubuntu.com/realtime"  # TODO


class RealtimeKernelEntitlement(repo.RepoEntitlement):
    name = "realtime-kernel"
    title = "Realtime Kernel"
    description = "Realtime Kernel"
    help_doc_url = REALTIME_KERNEL_DOCS_URL
    repo_key_file = "ubuntu-advantage-realtime-kernel.gpg"  # TODO
    is_beta = True

    @property
    def incompatible_services(self) -> Tuple[IncompatibleService, ...]:
        from uaclient.entitlements.fips import (
            FIPSEntitlement,
            FIPSUpdatesEntitlement,
        )

        return (
            IncompatibleService(
                FIPSEntitlement, messages.REALTIME_FIPS_INCOMPATIBLE
            ),
            IncompatibleService(
                FIPSUpdatesEntitlement,
                messages.REALTIME_FIPS_UPDATES_INCOMPATIBLE,
            ),
        )

    @property
    def messaging(self,) -> MessagingOperationsDict:
        # TODO
        return {
            "post_enable": [
                (
                    "Visit {} for more information on Ubuntu's"
                    " Realtime Kernel"
                ).format(REALTIME_KERNEL_DOCS_URL)
            ]
        }
