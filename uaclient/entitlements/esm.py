import os
from typing import Tuple, Type, Union, Optional

from uaclient import gpg, system
from uaclient.apt import APT_KEYS_DIR, ESM_REPO_FILE_CONTENT, KEYRINGS_DIR
from uaclient.defaults import ESM_APT_ROOTDIR
from uaclient.entitlements import repo
from uaclient.entitlements.base import UAEntitlement
from uaclient.entitlements.entitlement_status import CanDisableFailure


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
        from uaclient.jobs.update_messaging import update_apt_and_motd_messages

        enable_performed = super()._perform_enable(silent=silent)
        if enable_performed:
            update_apt_and_motd_messages(self.cfg)
        return enable_performed

    def disable(
        self, silent=False
    ) -> Tuple[bool, Union[None, CanDisableFailure]]:
        from uaclient.jobs.update_messaging import update_apt_and_motd_messages

        disable_performed, fail = super().disable(silent=silent)
        if disable_performed:
            update_apt_and_motd_messages(self.cfg)
        return disable_performed, fail

    def setup_local_esm_repo(self) -> None:
        series = system.get_platform_info()["series"]
        # Ugly? Yes, but so is python < 3.8 without removeprefix
        assert self.name.startswith("esm-")
        esm_name = self.name[len("esm-") :]
        repo_filename = os.path.normpath(
            ESM_APT_ROOTDIR + self.repo_list_file_tmpl.format(name=self.name),
        )
        keyring_file = self.repo_key_file

        # No need to create if already present
        if os.path.exists(repo_filename):
            return

        system.write_file(
            repo_filename,
            ESM_REPO_FILE_CONTENT.format(name=esm_name, series=series),
        )

        # Set up GPG key
        source_keyring_file = os.path.join(KEYRINGS_DIR, keyring_file)
        destination_keyring_file = os.path.normpath(
            ESM_APT_ROOTDIR + APT_KEYS_DIR + keyring_file
        )
        os.makedirs(os.path.dirname(destination_keyring_file), exist_ok=True)
        gpg.export_gpg_key(source_keyring_file, destination_keyring_file)

    def disable_local_esm_repo(self) -> None:
        keyring_file = os.path.normpath(
            ESM_APT_ROOTDIR + APT_KEYS_DIR + self.repo_key_file
        )
        repo_filename = os.path.normpath(
            ESM_APT_ROOTDIR + self.repo_list_file_tmpl.format(name=self.name),
        )
        system.remove_file(repo_filename)
        system.remove_file(keyring_file)


class ESMAppsEntitlement(ESMBaseEntitlement):
    origin = "UbuntuESMApps"
    name = "esm-apps"
    title = "Ubuntu Pro: ESM Apps"
    description = "Expanded Security Maintenance for Applications"
    repo_key_file = "ubuntu-advantage-esm-apps.gpg"

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
