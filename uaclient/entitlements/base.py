import abc
import os
import platform
import six

from uaclient import config
from uaclient import status


@six.add_metaclass(abc.ABCMeta)
class UAEntitlement(object):

    # The lowercase name of this entitlement
    name = None
    # The human readable title of this entitlement
    title = None
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

    def can_disable(self):
        """Report whether or not disabling is possible for the entitlement."""
        if os.getuid() != 0:
            print(status.MESSAGE_NONROOT_USER)
            return False
        entitlements = self.cfg.entitlements
        if not entitlements:
            print(status.MESSAGE_UNATTACHED)
            return False
        if not entitlements.get(self.name, {}).get('enabled'):
            print(status.MESSAGE_UNENTITLED_TMPL.format(title=self.title))
            return False
        if self.operational_status() == status.INACTIVE:
            print(
                status.MESSAGE_ALREADY_DISABLED_TMPL.format(title=self.title))
            return False
        return True

    def can_enable(self):
        """Report whether or not enabling is possible for the entitlement."""
        if os.getuid() != 0:
            print(status.MESSAGE_NONROOT_USER)
            return False
        entitlements = self.cfg.entitlements
        if not entitlements:
            print(status.MESSAGE_UNATTACHED)
            return False
        if not entitlements.get(self.name, {}).get('enabled'):
            print(status.MESSAGE_UNENTITLED_TMPL.format(title=self.title))
            return False
        if self.operational_status() == status.ACTIVE:
            print(status.MESSAGE_ALREADY_ENABLED_TMPL.format(title=self.title))
            return False
        if self.operational_status() == status.INAPPLICABLE:
            series = platform.dist()[2]
            print(status.MESSAGE_INAPPLICABLE_TMPL.format(
                title=self.title, series=series))
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
        entitlement_status = entitlements.get(self.name)
        if entitlement_status.get('enabled'):
            return status.ENTITLED
        return status.UNENTITLED

    @abc.abstractmethod
    def operational_status(self):
        """Return whether entitlement is ACTIVE, INACTIVE or UNAVILABLE"""
        pass
