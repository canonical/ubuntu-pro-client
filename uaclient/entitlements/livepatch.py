import os
import json
from uaclient.entitlements import base
from uaclient.status import (
    ACTIVE, INACTIVE, ENTITLED, UNENTITLED, EntitlementStatus)
from uaclient import util


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
        if not util.which('canonical-livepatch'):
            operational_status = INACTIVE
        else:
            operational_status = ACTIVE
        return EntitlementStatus(self.contract_status(), operational_status)
