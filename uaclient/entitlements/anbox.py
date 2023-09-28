from typing import Any, Dict, Optional, Tuple

from uaclient import contract, event_logger, messages, system
from uaclient.entitlements.entitlement_status import (
    CanEnableFailure,
    CanEnableFailureReason,
)
from uaclient.entitlements.repo import RepoEntitlement
from uaclient.files.state_files import (
    AnboxCloudData,
    anbox_cloud_credentials_file,
)
from uaclient.types import MessagingOperationsDict

event = event_logger.get_event_logger()


class AnboxEntitlement(RepoEntitlement):
    name = "anbox-cloud"
    title = messages.ANBOX_TITLE
    description = messages.ANBOX_DESCRIPTION
    help_doc_url = messages.urls.ANBOX_HOME_PAGE
    help_text = messages.ANBOX_HELP_TEXT
    repo_key_file = "ubuntu-pro-anbox-cloud.gpg"
    repo_url_tmpl = "{}"
    affordance_check_series = True
    supports_access_only = True
    origin = "Anbox"

    @property
    def messaging(self) -> MessagingOperationsDict:
        if not self.access_only:
            return {"post_enable": [messages.ANBOX_RUN_INIT_CMD]}
        else:
            return {}

    def can_enable(self) -> Tuple[bool, Optional[CanEnableFailure]]:
        ret, reason = super().can_enable()

        if not ret:
            return ret, reason

        if system.is_container() and not self.access_only:
            return (
                False,
                CanEnableFailure(
                    CanEnableFailureReason.ONLY_ACCESS_ONLY_SUPPORTED,
                    messages.ANBOX_FAIL_TO_ENABLE_ON_CONTAINER,
                ),
            )

        return True, None

    def _perform_enable(self, silent: bool = False) -> bool:
        ret = super()._perform_enable(silent=silent)

        if not ret:
            return ret

        directives = self.entitlement_cfg.get("entitlement", {}).get(
            "directives", {}
        )
        machine_token = self.cfg.machine_token["machineToken"]
        client = contract.UAContractClient(self.cfg)
        anbox_images_machine_access = client.get_resource_machine_access(
            machine_token, "anbox-images", save_file=False
        )

        anbox_cloud_data = AnboxCloudData(
            anbox_images_url=anbox_images_machine_access.get("entitlement", {})
            .get("directives", {})
            .get("url", ""),
            anbox_images_resource_token=anbox_images_machine_access.get(
                "resourceToken", ""
            ),
            anbox_cloud_apt_url=directives.get("aptURL", ""),
            anbox_cloud_apt_token=directives.get("aptKey", ""),
        )

        anbox_cloud_credentials_file.write(anbox_cloud_data)

        return True

    def _perform_disable(self, silent=False):
        super()._perform_disable(silent=silent)
        anbox_cloud_credentials_file.delete()
        return True

    # TODO: remove this function
    # This is just a placeholder until we can deliver the Anbox
    # resourceToken from the contracts without relying on the
    # enableByDefault obligation
    def _should_enable_by_default(
        self, obligations: Dict[str, Any], resourceToken: Optional[str]
    ) -> bool:
        return False
