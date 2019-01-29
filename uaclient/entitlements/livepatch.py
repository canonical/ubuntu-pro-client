import logging

from uaclient.entitlements import base
from uaclient import status
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
    static_affordances = (
        ('Cannot install Livepatch on a container', util.is_container, False),)

    def enable(self):
        """Enable specific entitlement.

        @return: True on success, False otherwise.
        """
        if not self.can_enable():
            return False
        if not util.which('/snap/bin/canonical-livepatch'):
            print('Installing canonical-livepatch snap...')
            util.subp(['snap', 'install', 'canonical-livepatch'], capture=True)
        livepatch_token = self.cfg.read_cache(
            'machine-access-%s' % self.name).get('resourceToken')
        if not livepatch_token:
            logging.debug(
                'No specific resourceToken present. Using machine token as'
                ' %s credentials', self.title)
            livepatch_token = self.cfg.machine_token['machineSecret']
        try:
            util.subp(['/snap/bin/canonical-livepatch', 'enable',
                       livepatch_token],
                      capture=True)
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

    def disable(self, silent=False, force=False):
        """Disable specific entitlement

        @return: True on success, False otherwise.
        """
        if not self.can_disable(silent, force):
            return False
        if not util.which('/snap/bin/canonical-livepatch'):
            return True
        util.subp(['/snap/bin/canonical-livepatch', 'disable'], capture=True)
        logging.debug('Removing canonical-livepatch snap...')
        if not silent:
            print('Removing canonical-livepatch snap...')
        util.subp(['snap', 'remove', 'canonical-livepatch'], capture=True)
        if not silent:
            print(status.MESSAGE_DISABLED_TMPL.format(title=self.title))
        return True

    def operational_status(self):
        """Return entitlement operational status as ACTIVE or INACTIVE."""
        passed_affordances, details = self.check_affordances()
        if not passed_affordances:
            return status.INAPPLICABLE, details
        operational_status = (status.ACTIVE, '')
        try:
            util.subp(['/snap/bin/canonical-livepatch', 'status'])
        except util.ProcessExecutionError as e:
            # TODO(May want to parse INACTIVE/failure assessment)
            logging.debug('Livepatch not enabled. %s', str(e))
            operational_status = (status.INACTIVE, str(e))
        return operational_status
