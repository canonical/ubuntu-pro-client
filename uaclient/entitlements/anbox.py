from typing import Any, Dict, Optional, Tuple

from uaclient import contract, event_logger, messages, system
from uaclient.entitlements.repo import RepoEntitlement
from uaclient.files.state_files import (
    AnboxCloudData,
    anbox_cloud_credentials_file,
)
from uaclient.types import MessagingOperationsDict, StaticAffordance

event = event_logger.get_event_logger()


class AnboxEntitlement(RepoEntitlement):
    name = "anbox-cloud"
    title = "Anbox Cloud"
    description = "Scalable Android in the cloud"
    help_doc_url = "https://anbox-cloud.io"
    repo_key_file = "ubuntu-pro-anbox-cloud.gpg"
    repo_url_tmpl = "{}"
    affordance_check_series = True
    supports_access_only = True

    @property
    def static_affordances(self) -> Tuple[StaticAffordance, ...]:
        return (
            (
                messages.SERVICE_ERROR_INSTALL_ON_CONTAINER.format(
                    title=self.title
                ),
                lambda: system.is_container(),
                False,
            ),
        )

    @property
    def messaging(self) -> MessagingOperationsDict:
        if not self.access_only:
            return {"post_enable": [messages.ANBOX_RUN_INIT_CMD.msg]}
        else:
            return {}

    def _perform_enable(self, silent: bool = False) -> Tuple[bool, bool]:
        ret, apt_update = super()._perform_enable(silent=silent)

        if not ret:
            return ret, apt_update

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

        return True, apt_update

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
