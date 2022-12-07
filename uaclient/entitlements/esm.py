from typing import Tuple, Type, Union

from uaclient.entitlements import repo
from uaclient.entitlements.base import UAEntitlement
from uaclient.entitlements.entitlement_status import CanDisableFailure
from uaclient.jobs.update_messaging import update_apt_and_motd_messages


class ESMBaseEntitlement(repo.RepoEntitlement):
    help_doc_url = "https://ubuntu.com/security/esm"

    @property
    def dependent_services(self) -> Tuple[Type[UAEntitlement], ...]:
        from uaclient.entitlements.ros import (
            ROSEntitlement,
            ROSUpdatesEntitlement,
        )

        return (ROSEntitlement, ROSUpdatesEntitlement)

    def _perform_enable(self, silent: bool = False) -> bool:
        enable_performed = super()._perform_enable(silent=silent)
        if enable_performed:
            update_apt_and_motd_messages(self.cfg)
        return enable_performed

    def disable(
        self, silent=False
    ) -> Tuple[bool, Union[None, CanDisableFailure]]:
        disable_performed, fail = super().disable(silent=silent)
        if disable_performed:
            update_apt_and_motd_messages(self.cfg)
        return disable_performed, fail


class ESMAppsEntitlement(ESMBaseEntitlement):
    origin = "UbuntuESMApps"
    name = "esm-apps"
    title = "Ubuntu Pro: ESM Apps"
    description = "Expanded Security Maintenance for Applications"
    repo_key_file = "ubuntu-advantage-esm-apps.gpg"
    is_beta = True


class ESMInfraEntitlement(ESMBaseEntitlement):
    name = "esm-infra"
    origin = "UbuntuESM"
    title = "Ubuntu Pro: ESM Infra"
    description = "Expanded Security Maintenance for Infrastructure"
    repo_key_file = "ubuntu-advantage-esm-infra-trusty.gpg"
