import abc
import six
import os

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

    def can_enable(self):
        """Test whether or not enabling is possible for the entitlement."""
        if os.getuid() != 0:
            print(status.MESSAGE_NONROOT_USER)
            return False
        entitlements = self.cfg.entitlements
        if not entitlements:
            print(status.MESSAGE_UNATTACHED)
            return False
        if not entitlements.get(self.name, {}).get('token'):
            print(status.MESSAGE_UNENTITLED_TMPL.format(title=self.title))
            return False
        if self.operational_status() == status.ACTIVE:
            print(status.MESSAGE_ALREADY_ENABLED_TMPL.format(name=self.name))
            return False
        return True

    @abc.abstractmethod
    def disable(self):
        """Disable specific entitlement

        @return: True on success, False otherwise.
        """
        pass

    def contract_status(self):
        """Return whether contract entitlement is ENTITLED or UNENTITLED."""
        entitlements = self.cfg.entitlements
        entitlement_status = entitlements['entitlements'].get(self.name)
        if entitlement_status.get('token'):
            return status.ENTITLED
        return status.UNENTITLED

    @abc.abstractmethod
    def operational_status(self):
        """Return whether entitlement is ACTIVE, INACTIVE or UNAVILABLE"""
        pass


def request_entitlements():
    return {}
