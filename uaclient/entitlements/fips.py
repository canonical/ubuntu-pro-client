from uaclient.entitlements import base
from uaclient.status import UNENTITLED, UNAVAILABLE, EntitlementStatus


class FIPSEntitlement(base.UAEntitlement):

    name = 'fips'
    description = 'Canonical FIPS 140-2 Certified Modules'

    def enable(self):
        """Enable specific entitlement.

        @return: True on success, False otherwise.
        """
        print('FIPS configured, please reboot to enable.')
        return True

    def disable(self):
        """Disable specific entitlement

        @return: True on success, False otherwise.
        """
        print('Warning: no option to disable FIPS')
        return False

    def status(self):
        """Return tuple contract_status, service_status"""
        return EntitlementStatus(UNENTITLED, UNAVAILABLE)


class FIPSUpdatesEntitlement(base.UAEntitlement):

    name = 'fips-updates'
    description = 'Canonical FIPS 140-2 Certified Modules'

    def enable(self):
        """Enable specific entitlement.

        @return: True on success, False otherwise.
        """
        print('FIPS Updates configured, please reboot to enable.')
        return True

    def disable(self):
        """Disable specific entitlement

        @return: True on success, False otherwise.
        """
        print('Warning: no option to disable FIPS Updates')
        return False

    def status(self):
        """Return tuple contract_status, service_status"""
        return EntitlementStatus(UNENTITLED, UNAVAILABLE)
