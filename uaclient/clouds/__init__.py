import abc


class UAPremiumCloudInstance(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def identity_doc(self) -> str:
        """Return the identity document representing this cloud instance"""
        pass

    @property
    @abc.abstractmethod
    def is_viable(self) -> bool:
        """Return True if the machine is a viable UAPremiumCloudInstance."""
        pass
