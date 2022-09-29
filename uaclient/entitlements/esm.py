import os
from typing import Optional, Tuple, Type, Union  # noqa: F401

from uaclient import apt, system
from uaclient.entitlements import repo
from uaclient.entitlements.base import UAEntitlement
from uaclient.entitlements.entitlement_status import CanDisableFailure
from uaclient.jobs.update_messaging import update_apt_and_motd_messages


class ESMBaseEntitlement(repo.RepoEntitlement):
    help_doc_url = "https://ubuntu.com/security/esm"
    repo_url = "https://esm.ubuntu.com/{service}"

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

    def setup_unauthenticated_repo(self):
        if not os.path.exists(self.repo_list_file_tmpl.format(name=self.name)):
            series = system.get_platform_info()["series"]
            apt.setup_unauthenticated_repo(
                repo_filename=self.repo_list_file_tmpl.format(name=self.name),
                repo_pref_filename=self.repo_pref_file_tmpl.format(
                    name=self.name
                ),
                repo_url=self.repo_url.format(service=self.apt_repo_name),
                keyring_file=self.repo_key_file,
                apt_origin=self.origin,
                suites=[
                    "{series}-{name}-security".format(
                        series=series, name=self.apt_repo_name
                    ),
                    "{series}-{name}-updates".format(
                        series=series, name=self.apt_repo_name
                    ),
                ],
            )


class ESMAppsEntitlement(ESMBaseEntitlement):
    origin = "UbuntuESMApps"
    name = "esm-apps"
    title = "Ubuntu Pro: ESM Apps"
    description = "Expanded Security Maintenance for Applications"
    repo_key_file = "ubuntu-advantage-esm-apps.gpg"
    apt_repo_name = "apps"
    is_beta = True

    @property
    def repo_pin_priority(self) -> Optional[str]:
        """All LTS should pin esm-apps."""
        series = system.get_platform_info()["series"]

        if self.valid_service:
            if system.is_lts(series):
                return "never"
        return None

    @property
    def disable_apt_auth_only(self) -> bool:
        """All LTS remove APT auth files upon disable"""
        series = system.get_platform_info()["series"]

        if self.valid_service:
            return system.is_lts(series)
        return False


class ESMInfraEntitlement(ESMBaseEntitlement):
    name = "esm-infra"
    origin = "UbuntuESM"
    title = "Ubuntu Pro: ESM Infra"
    description = "Expanded Security Maintenance for Infrastructure"
    repo_key_file = "ubuntu-advantage-esm-infra-trusty.gpg"
    apt_repo_name = "infra"

    @property
    def repo_pin_priority(self) -> Optional[str]:
        """All LTS are entitled to ESM Infra."""
        if system.is_lts(system.get_platform_info()["series"]):
            return "never"
        return None  # No pinning on non-LTS releases

    @property
    def disable_apt_auth_only(self) -> bool:
        """Ubuntu EOL releases are in active ESM.

        Leave unauthenticated APT sources on disk with never pinning to ensure
        visibility to UA ESM: Infra packages for MOTD/APT messaging.
        """
        return system.is_active_esm(system.get_platform_info()["series"])
