import logging

from uaclient.entitlements import base
from uaclient import apt, exceptions, status
from uaclient import util
from uaclient.status import ApplicationStatus

SNAP_CMD = '/usr/bin/snap'
SNAP_INSTALL_RETRIES = [0.5, 1.0, 5.0]

try:
    from typing import Any, Dict, Tuple  # noqa: F401
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass

ERROR_MSG_MAP = {
    'Unknown Auth-Token': 'Invalid Auth-Token provided to livepatch.',
    'unsupported kernel': 'Your running kernel is not supported by Livepatch.',
}


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
            if not util.which(SNAP_CMD):
                print('Installing snapd')
                util.subp(['apt-get', 'install', '--assume-yes', 'snapd'],
                          capture=True, retry_sleeps=apt.APT_RETRIES)
                util.subp([SNAP_CMD, 'wait', 'system', 'seed.loaded'],
                          capture=True)
            elif 'snapd' not in apt.get_installed_packages():
                raise exceptions.UserFacingError(
                    '/usr/bin/snap is present but snapd is not installed;'
                    ' cannot enable {}'.format(self.title))
            print('Installing canonical-livepatch snap')
            try:
                util.subp([SNAP_CMD, 'install', 'canonical-livepatch'],
                          capture=True, retry_sleeps=SNAP_INSTALL_RETRIES)
            except util.ProcessExecutionError as e:
                msg = 'Unable to install Livepatch client: ' + str(e)
                print(msg)
                logging.error(msg)
                return False
        return self.setup_livepatch_config(
            process_directives=True, process_token=True)

    def setup_livepatch_config(
            self, process_directives: bool = True,
            process_token: bool = True) -> bool:
        """Processs configuration setup for livepatch directives.

        :param process_directives: Boolean set True when directives should be
            processsed.
        :param process_token: Boolean set True when token should be
            processsed.
        """
        entitlement_cfg = self.cfg.entitlements.get(self.name)
        if process_directives:
            try:
                process_config_directives(entitlement_cfg)
            except util.ProcessExecutionError as e:
                msg = 'Unable to configure Livepatch: ' + str(e)
                print(msg)
                logging.error(msg)
                return False
        if process_token:
            livepatch_token = entitlement_cfg.get('resourceToken')
            if not livepatch_token:
                logging.debug(
                    'No specific resourceToken present. Using machine token as'
                    ' %s credentials', self.title)
                livepatch_token = self.cfg.machine_token['machineToken']
            application_status, _details = self.application_status()
            if application_status != status.ApplicationStatus.DISABLED:
                logging.info('Disabling %s prior to re-attach with new token',
                             self.title)
                try:
                    util.subp(['/snap/bin/canonical-livepatch', 'disable'])
                except util.ProcessExecutionError as e:
                    logging.error(str(e))
                    return False
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

    def disable(self, silent=False):
        """Disable specific entitlement

        @return: True on success, False otherwise.
        """
        if not self.can_disable(silent):
            return False
        if not util.which('/snap/bin/canonical-livepatch'):
            return True
        util.subp(['/snap/bin/canonical-livepatch', 'disable'], capture=True)
        logging.debug('Removing canonical-livepatch snap')
        if not silent:
            print('Removing canonical-livepatch snap')
        util.subp([SNAP_CMD, 'remove', 'canonical-livepatch'],
                  capture=True)
        if not silent:
            print(status.MESSAGE_DISABLED_TMPL.format(title=self.title))
        return True

    def application_status(self) -> 'Tuple[ApplicationStatus, str]':
        status = (ApplicationStatus.ENABLED, '')
        try:
            util.subp(['/snap/bin/canonical-livepatch', 'status'])
        except util.ProcessExecutionError as e:
            # TODO(May want to parse INACTIVE/failure assessment)
            logging.debug('Livepatch not enabled. %s', str(e))
            status = (ApplicationStatus.DISABLED, str(e))
        return status

    def process_contract_deltas(
            self, orig_access: 'Dict[str, Any]',
            deltas: 'Dict[str, Any]', allow_enable: bool = False) -> bool:
        """Process any contract access deltas for this entitlement.

        :param orig_access: Dictionary containing the original
            resourceEntitlement access details.
        :param deltas: Dictionary which contains only the changed access keys
        and values.
        :param allow_enable: Boolean set True if allowed to perform the enable
            operation. When False, a message will be logged to inform the user
            about the recommended enabled service.

        :return: True when delta operations are processed; False when noop.
        """
        if super().process_contract_deltas(orig_access, deltas, allow_enable):
            return True  # Already processed parent class deltas
        application_status, _ = self.application_status()
        if application_status == status.ApplicationStatus.DISABLED:
            return True  # only operate on changed directives when ACTIVE
        delta_entitlement = deltas.get('entitlement', {})
        delta_directives = delta_entitlement.get('directives', {})
        supported_deltas = set(['caCerts', 'remoteServer'])
        process_directives = bool(
            supported_deltas.intersection(delta_directives))
        process_token = bool(deltas.get('resourceToken', False))
        if any([process_directives, process_token]):
            logging.info(
                "Updating '%s' on changed directives." % self.name)
            return self.setup_livepatch_config(
                process_directives=process_directives,
                process_token=process_token)
        return True


def process_config_directives(cfg):
    """Process livepatch configuration directives.

    We process caCerts before remoteServer because changing remote-server
    in the canonical-livepatch CLI performs a PUT against the new server name.
    If new caCerts were required for the new remoteServer, this
    canonical-livepatch client PUT could fail on unmatched old caCerts.

    @raises: ProcessExecutionError if unable to configure livepatch.
    """
    if not cfg:
        return
    directives = cfg.get('entitlement', {}).get('directives', {})
    ca_certs = directives.get('caCerts')
    if ca_certs:
        util.subp(['/snap/bin/canonical-livepatch', 'config',
                   'ca-certs=%s' % ca_certs], capture=True)
    remote_server = directives.get('remoteServer', '')
    if remote_server.endswith('/'):
        remote_server = remote_server[:-1]
    if remote_server:
        util.subp(['/snap/bin/canonical-livepatch', 'config',
                   'remote-server=%s' % remote_server], capture=True)
