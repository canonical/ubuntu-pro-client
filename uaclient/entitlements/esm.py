from uaclient.entitlements import base
from uaclient.status import ENTITLED, INACTIVE


class ESMEntitlement(base.UAEntitlement):

    name = 'esm'
    title = 'Extended Security Maintenance'
    description = (
        'Ubuntu Extended Security Maintenance archive'
        ' (https://ubuntu.com/esm)')

    def enable(self):
        """Enable specific entitlement.

        @return: True on success, False otherwise.
        """
        if not self.can_enable():
            return False
        print('Extended Security and Maintenance archive access enabled.')
        return True

    def disable(self):
        """Disable specific entitlement

        @return: True on success, False otherwise.
        """
        print('Extended Security and Maintenance archive access disabled.')
        return True

    def operational_status(self):
        """Return operational status of ESM service."""
        return INACTIVE
