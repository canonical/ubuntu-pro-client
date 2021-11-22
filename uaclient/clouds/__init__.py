import abc
from typing import Any, Callable, Dict, Optional

from uaclient import config


class AutoAttachCloudInstance(metaclass=abc.ABCMeta):
    def __init__(self, cfg: config.UAConfig):
        self.cfg = cfg

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

    @property
    @abc.abstractmethod
    def is_viable(self) -> bool:
        """Return True if the machine is a viable AutoAttachCloudInstance."""
        pass

    @abc.abstractmethod
    def is_license_present(self) -> bool:
        """
        Synchronously check for an Ubuntu Pro license
        """
        pass

    @abc.abstractmethod
    def should_poll_for_license(self) -> bool:
        """
        Cloud-specific checks for whether the daemon should continously poll
        for Ubuntu Pro licenses.
        """
        pass

    @abc.abstractmethod
    def get_polling_fn(self) -> Optional[Callable]:
        """
        Returns a function that continously polls for Ubuntu Pro licenses.
        The function should auto-attach and cleanly return when a license is
        found.
        """
        pass
