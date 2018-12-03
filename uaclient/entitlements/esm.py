from uaclient.entitlements import base
from uaclient.status import ENTITLED, INACTIVE, EntitlementStatus


class ESMEntitlement(base.UAEntitlement):

    name = 'esm'
    description = (
        'Ubuntu Extended Security Maintenance archive'
        ' (https://ubuntu.com/esm)')

    def enable(self):
        """Enable specific entitlement.

        @return: True on success, False otherwise.
        """
        print('Extended Security and Maintenance archive access enabled.')
        return True

    def disable(self):
        """Disable specific entitlement

        @return: True on success, False otherwise.
        """
        print('Extended Security and Maintenance archive access disabled.')
        return True

    def status(self):
        """Return EntitlementStatus tuple"""
        return EntitlementStatus(self.contract_status(), INACTIVE)
