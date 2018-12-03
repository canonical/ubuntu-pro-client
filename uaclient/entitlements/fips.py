from uaclient.entitlements import base
from uaclient.status import UNENTITLED, INAPPLICABLE


class FIPSEntitlement(base.UAEntitlement):

    name = 'fips'
    title = 'FIPS'
    description = 'Canonical FIPS 140-2 Certified Modules'

    def enable(self):
        """Enable specific entitlement.

        @return: True on success, False otherwise.
        """
        if not self.can_enable():
            return False
        print('FIPS configured, please reboot to enable.')
        return True

    def disable(self):
        """Disable specific entitlement

        @return: True on success, False otherwise.
        """
        if not self.can_disable():
            return False
        print('Warning: no option to disable FIPS')
        return False

    def operational_status(self):
        """Return operational status of FIPS entitlement."""
        return INAPPLICABLE


class FIPSUpdatesEntitlement(base.UAEntitlement):

    name = 'fips-updates'
    title = 'FIPS Updates'
    description = 'Canonical FIPS 140-2 Certified Modules'

    def enable(self):
        """Enable specific entitlement.

        @return: True on success, False otherwise.
        """
        if not self.can_enable():
            return False
        print('FIPS Updates configured, please reboot to enable.')
        return True

    def disable(self):
        """Disable specific entitlement

        @return: True on success, False otherwise.
        """
        if not self.can_disable():
            return False
        print('Warning: no option to disable FIPS Updates')
        return False

    def operational_status(self):
        """Return operational status of FIPS-updates entitlement."""
        return INAPPLICABLE
