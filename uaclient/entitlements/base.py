import abc
import six
from uaclient import config
from uaclient import status


@six.add_metaclass(abc.ABCMeta)
class UAEntitlement(object):

    # The lowercase name of this entitlement
    name = None
    # A sentence describing this entitlement
    description = None

    def __init__(self, cfg=None):
        """Setup UAEntitlement instance

        @param config: Parsed configuration dictionary
        """
        if not cfg:
            cfg = config.UAConfig()
        self.cfg = cfg

    @abc.abstractmethod
    def enable(self):
        """Enable specific entitlement.

        @return: True on success, False otherwise.
        """
        pass

    @abc.abstractmethod
    def disable(self):
        """Disable specific entitlement

        @return: True on success, False otherwise.
        """
        pass

    def contract_status(self):
        """Return whether contract entitlement is ENABLED or DISABLED."""
        entitlements = self.cfg.entitlements
        entitlement_status = entitlements['entitlements'].get(self.name)
        if entitlement_status.get('token'):
            return status.ENTITLED
        return status.UNENTITLED

    @abc.abstractmethod
    def status(self):
        """Return EntitlementStatus tuple"""
        pass


def request_entitlements():
    return {}
