import abc
import six


@six.add_metaclass(abc.ABCMeta)
class UAEntitlement(object):

    # The lowercase name of this entitlement
    name = None
    # A sentence describing this entitlement
    description = None

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

    @abc.abstractmethod
    def status(self):
        """Return EntitlementStatus tuple"""
        pass


def request_entitlements():
    return {}
