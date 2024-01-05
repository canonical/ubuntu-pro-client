import os
from typing import Tuple, Type, Union

from uaclient import messages, system
from uaclient.apt import APT_KEYS_DIR, DEB822_REPO_FILE_CONTENT, KEYRINGS_DIR
from uaclient.defaults import ESM_APT_ROOTDIR
from uaclient.entitlements import repo
from uaclient.entitlements.base import UAEntitlement
from uaclient.entitlements.entitlement_status import CanDisableFailure
from uaclient.util import set_filename_extension


class ESMBaseEntitlement(repo.RepoEntitlement):
    help_doc_url = messages.urls.ESM_HOME_PAGE

    @property
    def dependent_services(self) -> Tuple[Type[UAEntitlement], ...]:
        from uaclient.entitlements.ros import (
            ROSEntitlement,
            ROSUpdatesEntitlement,
        )

        return (ROSEntitlement, ROSUpdatesEntitlement)

    def _perform_enable(self, silent: bool = False) -> bool:
        from uaclient.timer.update_messaging import update_motd_messages

        enable_performed = super()._perform_enable(silent=silent)
        if enable_performed:
            update_motd_messages(self.cfg)
            self.disable_local_esm_repo()
        return enable_performed

    def setup_local_esm_repo(self) -> None:
        series = system.get_release_info().series
        # Ugly? Yes, but so is python < 3.8 without removeprefix
        assert self.name.startswith("esm-")
        esm_name = self.name[len("esm-") :]
        sources_repo_filename = set_filename_extension(
            os.path.normpath(
                ESM_APT_ROOTDIR + self.repo_file,
            ),
            "sources",
        )
        list_repo_filename = set_filename_extension(
            os.path.normpath(
                ESM_APT_ROOTDIR + self.repo_file,
            ),
            "list",
        )

        # No need to create if any format already present
        if os.path.exists(sources_repo_filename) or os.path.exists(
            list_repo_filename
        ):
            return

        esm_url = "https://esm.ubuntu.com/{name}/ubuntu".format(name=esm_name)
        suites = "{series}-{name}-security {series}-{name}-updates".format(
            series=series, name=esm_name
        )

        # When writing, use the sources format by default
        system.write_file(
            sources_repo_filename,
            DEB822_REPO_FILE_CONTENT.format(
                url=esm_url,
                suites=suites,
                keyrings_dir=KEYRINGS_DIR,
                keyring_file=self.repo_key_file,
                deb_src="",
            ),
        )

    def disable_local_esm_repo(self) -> None:
        keyring_file = os.path.normpath(
            ESM_APT_ROOTDIR + APT_KEYS_DIR + self.repo_key_file
        )
        system.ensure_file_absent(keyring_file)

        repo_filename = os.path.normpath(
            ESM_APT_ROOTDIR + self.repo_file,
        )
        # Remove any instance of the file present in the folder
        system.ensure_file_absent(
            set_filename_extension(repo_filename, "sources")
        )
        system.ensure_file_absent(
            set_filename_extension(repo_filename, "list")
        )


class ESMAppsEntitlement(ESMBaseEntitlement):
    origin = "UbuntuESMApps"
    name = "esm-apps"
    title = messages.ESM_APPS_TITLE
    description = messages.ESM_APPS_DESCRIPTION
    help_text = messages.ESM_APPS_HELP_TEXT
    repo_key_file = "ubuntu-pro-esm-apps.gpg"

    def disable(
        self, silent=False
    ) -> Tuple[bool, Union[None, CanDisableFailure]]:
        from uaclient.timer.update_messaging import update_motd_messages

        disable_performed, fail = super().disable(silent=silent)
        if disable_performed:
            update_motd_messages(self.cfg)
            if system.is_current_series_lts():
                self.setup_local_esm_repo()
        return disable_performed, fail


class ESMInfraEntitlement(ESMBaseEntitlement):
    name = "esm-infra"
    origin = "UbuntuESM"
    title = messages.ESM_INFRA_TITLE
    description = messages.ESM_INFRA_DESCRIPTION
    help_text = messages.ESM_INFRA_HELP_TEXT
    repo_key_file = "ubuntu-pro-esm-infra.gpg"

    def disable(
        self, silent=False
    ) -> Tuple[bool, Union[None, CanDisableFailure]]:
        from uaclient.timer.update_messaging import update_motd_messages

        disable_performed, fail = super().disable(silent=silent)
        if disable_performed:
            update_motd_messages(self.cfg)
            if system.is_current_series_active_esm():
                self.setup_local_esm_repo()
        return disable_performed, fail
