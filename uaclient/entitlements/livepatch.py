import logging
import os
import json

from uaclient import status
from uaclient.entitlements import base
from uaclient.status import (
    ACTIVE, INACTIVE, ENTITLED, UNENTITLED, MESSAGE_DISABLED_TMPL)
from uaclient import util


ERROR_MSG_MAP = {
 'Unknown Auth-Token': 'Invalid Auth-Token provided to livepatch.',
 'unsupported kernel': 'Your running kernel is not supported by Livepatch.',
}


class LivepatchEntitlement(base.UAEntitlement):

    name = 'livepatch'
    title = 'Livepatch'
    description = (
        'Canonical Livepatch Service'
        ' (https://www.ubuntu.com/server/livepatch)')

    def enable(self):
        """Enable specific entitlement.

        @return: True on success, False otherwise.
        """
        if not self.can_enable():
            return False
        if not util.which('canonical-livepatch'):
            print('Installing canonical-livepatch snap...')
            util.subp(['snap', 'install', 'canonical-livepatch'])
        livepatch_token = (
            self.cfg.entitlements['entitlements']['livepatch']['token'])
        try:
            util.subp(['canonical-livepatch', 'enable', livepatch_token])
        except util.ProcessExecutionError as e:
            msg = 'Unable to enable Livepatch: '
            for error_message, print_message in ERROR_MSG_MAP.items():
                if error_message in str(e):
                    msg += print_message
                    break
            if msg == 'Unable to enable Livepatch: ':
               msg += str(e)
            print(msg)
            return False
        print('Canonical livepatch enabled.')
        return True

    def disable(self):
        """Disable specific entitlement

        @return: True on success, False otherwise.
        """
        if not self.can_disable():
            return False
        util.subp(['canonical-livepatch', 'disable'])
        logging.debug('Removing canonical-livepatch snap')
        util.subp(['snap', 'remove', 'canonical-livepatch'])
        print(MESSAGE_DISABLED_TMPL.format(title=self.title))
        return True

    def operational_status(self):
        """Return entitlement operational status as ACTIVE or INACTIVE."""
        operational_status = ACTIVE
        try:
            util.subp(['canonical-livepatch', 'status'])
        except util.ProcessExecutionError as e:
            # TODO: May want to parse INACTIVE/failure assessment
            logging.debug('Livepatch not enabled. %s', str(e))
            operational_status = INACTIVE
        return operational_status
