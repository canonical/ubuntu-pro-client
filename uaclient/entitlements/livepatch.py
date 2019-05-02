import logging

from uaclient.entitlements import base
from uaclient import status
from uaclient import util


ERROR_MSG_MAP = {
    'Unknown Auth-Token': 'Invalid Auth-Token provided to livepatch.',
    'unsupported kernel': 'Your running kernel is not supported by Livepatch.',
}

PATCH_STATE_UNKNOWN_TMPL = '''\
 * Livepatch is in an unknown patch status '{patch_state}'
    - Please see /var/log/syslog for more information.'''

PATCH_STATE_MSG_MAP = {
    'unapplied': 'Patches are available and will be deployed shortly.',
    'applied': 'All available patches applied.',
    'applied-with-bug': (
        'Live patching failed, please run `ubuntu-bug linux` to report a bug'
    ),
    'apply-failed': (
        'Live patching failed, please run `ubuntu-bug linux` to report a bug'
    ),
    'nothing-to-apply': 'All available patches applied.',
    'applying': 'Live patching currently in progress.'
}

CHECK_STATE_UNKNOWN_TMPL = '''\
 * Livepatch is in an unknown check state '{check_state}'
    - Please see /var/log/syslog for more information.'''

CHECK_STATE_MSG_MAP = {
    'needs-check': 'Regular server check is pending.',
    'check-failed': (
        'Livepatch server check failed.\n'
        '    Please see /var/log/syslog for more information.'
    ),
    'checked': PATCH_STATE_MSG_MAP
}

STATUS_LIVEPATCH_ENABLED = ' * Canonical Livepatch is enabled.'
STATUS_LIVEPATCH_ENTITLED = '''\
 * Canonical Livepatch is available for installation.
   - Reduce system reboots and improve kernel security. Enable with:
     `ua enable livepatch`'''
STATUS_LIVEPATCH_DISABLED_KERNEL_TMPL = '''\
 * Canonical Livepatch is installed but disabled.
   - Custom kernel {kernel_ver} is not supported\
 (https://bit.ly/livepatch-faq)'''


class LivepatchEntitlement(base.UAEntitlement):

    name = 'livepatch'
    title = 'Livepatch'
    description = (
        'Canonical Livepatch Service'
        ' (https://ubuntu.com/livepatch)')

    # Use a lambda so we can mock util.is_container in tests
    static_affordances = (
        ('Cannot install Livepatch on a container',
         lambda: util.is_container(),
         False),)

    def enable(self, *, silent_if_inapplicable: bool = False) -> bool:
        """Enable specific entitlement.

        :param silent_if_inapplicable:
            Don't emit any messages until after it has been determined that
            this entitlement is applicable to the current machine.

        @return: True on success, False otherwise.
        """
        if not self.can_enable(silent=silent_if_inapplicable):
            return False
        if not util.which('/snap/bin/canonical-livepatch'):
            if not util.which('snap'):
                print('Installing snapd...')
                util.subp(['apt-get', 'install', '--assume-yes', 'snapd'],
                          capture=True)
                util.subp(['snap', 'wait', 'system', 'seed.loaded'],
                          capture=True)
            print('Installing canonical-livepatch snap...')
            try:
                util.subp(['snap', 'install', 'canonical-livepatch'],
                          capture=True)
            except util.ProcessExecutionError as e:
                msg = 'Unable to install Livepatch client: ' + str(e)
                print(msg)
                logging.error(msg)
                return False
        entitlement_cfg = self.cfg.entitlements.get(self.name)
        try:
            process_directives(entitlement_cfg)
        except util.ProcessExecutionError as e:
            msg = 'Unable to configure Livepatch: ' + str(e)
            print(msg)
            logging.error(msg)
            return False
        livepatch_token = entitlement_cfg.get('resourceToken')
        if not livepatch_token:
            logging.debug(
                'No specific resourceToken present. Using machine token as'
                ' %s credentials', self.title)
            livepatch_token = self.cfg.machine_token['machineToken']
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
        entitlement_cfg = self.cfg.entitlements.get(self.name)
        if not entitlement_cfg:
            return status.INAPPLICABLE, '%s is not entitled' % self.title
        elif entitlement_cfg['entitlement'].get('entitled', False) is False:
            return status.INAPPLICABLE, '%s is not entitled' % self.title
        operational_status = (status.ACTIVE, '')
        try:
            util.subp(['/snap/bin/canonical-livepatch', 'status'])
        except util.ProcessExecutionError as e:
            # TODO(May want to parse INACTIVE/failure assessment)
            logging.debug('Livepatch not enabled. %s', str(e))
            operational_status = (status.INACTIVE, str(e))
        return operational_status


def process_directives(cfg):
    """Process livepatch configuration directives.

    @raises: ProcessExecutionError if unable to configure livepatch.
    """
    if not cfg:
        return
    directives = cfg.get('entitlement', {}).get('directives', {})
    remote_server = directives.get('remoteServer', '')
    if remote_server.endswith('/'):
        remote_server = remote_server[:-1]
    if remote_server:
        util.subp(['/snap/bin/canonical-livepatch', 'config',
                   'remote-server=%s' % remote_server], capture=True)
    ca_certs = directives.get('caCerts')
    if ca_certs:
        util.subp(['/snap/bin/canonical-livepatch', 'config',
                   'ca-certs=%s' % ca_certs], capture=True)
