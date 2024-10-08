import abc
from typing import Any, Dict

from uaclient import config, contract


class AutoAttachInstance(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def is_viable(self) -> bool:
        """Return True if the machine is a viable AutoAttachCloudInstance."""
        pass

    @abc.abstractmethod
    def acquire_pro_token(self, cfg: config.UAConfig) -> str:
        """
        Cloud-specific implementation of acquiring the pro token using whatever
        method suits the platform
        """
        pass

    @abc.abstractmethod
    def should_poll_for_pro_license(self) -> bool:
        """
        Cloud-specific checks for whether the daemon should continously poll
        for Ubuntu Pro licenses.
        """
        pass

    @abc.abstractmethod
    def is_pro_license_present(self, *, wait_for_change: bool) -> bool:
        """
        Check for an Ubuntu Pro license
        """
        pass


class PublicCloudAutoAttachInstance(AutoAttachInstance, metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def identity_doc(self) -> Dict[str, Any]:
        """Return the identity document representing this cloud instance"""
        pass

    @property
    @abc.abstractmethod
    def cloud_type(self) -> str:
        """Return a string of the cloud type on which this instance runs"""
        pass

    def acquire_pro_token(self, cfg: config.UAConfig) -> str:
        """
        Cloud-specific implementation of acquiring the pro token using whatever
        method suits the platform
        """
        contract_client = contract.UAContractClient(cfg)
        token_response = contract_client.get_contract_token_for_cloud_instance(
            cloud_type=self.cloud_type, data=self.identity_doc
        )
        return token_response["contractToken"]
