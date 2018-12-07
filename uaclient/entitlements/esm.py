from uaclient.entitlements import base
from uaclient import status


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
        if not self.can_disable():
            return False
        print(status.MESSAGE_DISABLED_TMPL.format(title=self.title))
        return True

    def operational_status(self):
        """Return operational status of ESM service."""
        return status.INACTIVE
