from uaclient.entitlements import base
from uaclient.status import ENTITLED, ACTIVE, EntitlementStatus


class LivepatchEntitlement(base.UAEntitlement):

    name = 'livepatch'
    description = (
        'Canonical Livepatch Service'
        ' (https://www.ubuntu.com/server/livepatch)')

    def enable(self):
        """Enable specific entitlement.

        @return: True on success, False otherwise.
        """
        print('Canonical livepatch enabled.')
        return True

    def disable(self):
        """Disable specific entitlement

        @return: True on success, False otherwise.
        """
        print('Canonical livepatch disabled.')
        return True

    def status(self):
        """Return tuple contract_status, service_status"""
        return EntitlementStatus(ENTITLED, ACTIVE)
