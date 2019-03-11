import logging
import re

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
        entitlement_cfg = self.cfg.entitlements.get(self.name)
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
        operational_status = (status.ACTIVE, '')
        try:
            util.subp(['/snap/bin/canonical-livepatch', 'status'])
        except util.ProcessExecutionError as e:
            # TODO(May want to parse INACTIVE/failure assessment)
            logging.debug('Livepatch not enabled. %s', str(e))
            operational_status = (status.INACTIVE, str(e))
        return operational_status

    def get_motd_summary(self):
        """Return the motd summary for livepatch status or empty string."""
        op_status, _details = self.operational_status()
        if op_status != status.ACTIVE:
            if util.which('/snap/bin/canonical-livepatch'):
                return ' * Canonical Livepatch is installed but disabled'
            return ''
        livepatch_status, _err = util.subp(
            ['/snap/bin/canonical-livepatch', 'status'])
        return livepatch_status_to_motd(livepatch_status)


def livepatch_status_to_motd(status_output):
    """Parse canonical-livepatch status output into motd status."""
    livepatch_state = patch_state = check_state = None
    # Parse status for livepatch patch and check states.
    for line in status_output.splitlines():
        match = re.match('.*running: (.*)$', line)
        if match:
            livepatch_state = 'enabled' if match.group(1) == 'true' else None
        match = re.match('.*patchState: (.*)$', line)
        if match:
            patch_state = match.group(1)
        match = re.match('.*checkState: (.*)$', line)
        if match:
            check_state = match.group(1)

    if livepatch_state == 'disabled (unsupported kernel)':
        kernel_ver = util.get_platform_info('kernel')
        return STATUS_LIVEPATCH_DISABLED_KERNEL_TMPL.format(
            kernel_ver=kernel_ver)

    if livepatch_state == 'enabled':
        motd_lines = [STATUS_LIVEPATCH_ENABLED]
        if check_state not in CHECK_STATE_MSG_MAP:
            return motd_lines.append(CHECK_STATE_UNKNOWN_TMPL.format(
                check_state=check_state))
        message_map = CHECK_STATE_MSG_MAP[check_state]
        if isinstance(message_map, str):
            motd_lines.append(message_map)
        else:
            prefix = '   - '
            if patch_state in message_map:
                motd_lines.append(prefix + message_map[patch_state])
            else:
                motd_lines.append(prefix + PATCH_STATE_UNKNOWN_TMPL.format(
                    patch_state=patch_state))
        return '\n'.join(motd_lines)
    return ''
