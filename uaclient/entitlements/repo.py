import glob
import logging
import os

from uaclient import apt
from uaclient.entitlements import base
from uaclient import status
from uaclient import util


class RepoEntitlement(base.UAEntitlement):

    repo_list_file_tmpl = '/etc/apt/sources.list.d/ubuntu-{name}-{series}.list'
    repo_pref_file_tmpl = '/etc/apt/preferences.d/ubuntu-{name}-{series}'
    origin = None   # The repo Origin value for setting pinning

    repo_url = 'UNSET'
    repo_key_file = 'UNSET'  # keyfile delivered by ubuntu-cloudimage-keyring
    repo_pin_priority = None      # Optional repo pin priority in subclass

    # Any custom messages to emit pre or post enable or disable operations
    messaging = {}  # Currently post_enable is used in CommonCriteria
    packages = []  # Debs to install on enablement

    def enable(self):
        """Enable specific entitlement.

        @return: True on success, False otherwise.
        """
        if not self.can_enable():
            return False
        series = util.get_platform_info('series')
        repo_filename = self.repo_list_file_tmpl.format(
            name=self.name, series=series)
        resource_cfg = self.cfg.entitlements.get(self.name)
        directives = resource_cfg['entitlement'].get('directives', {})
        token = resource_cfg.get('resourceToken')
        if not token:
            logging.debug(
                'No specific resourceToken present. Using machine token'
                ' as %s credentials', self.title)
            token = self.cfg.machine_token['machineSecret']
        ppa_fingerprint = directives.get('aptKey')
        if ppa_fingerprint:
            keyring_file = None
        else:
            keyring_file = os.path.join(apt.KEYRINGS_DIR, self.repo_key_file)
        repo_url = directives.get('aptURL')
        if not repo_url:
            repo_url = self.repo_url
        try:
            apt.add_auth_apt_repo(
                repo_filename, repo_url, token, keyring_file, ppa_fingerprint)
        except apt.InvalidAPTCredentialsError as e:
            logging.error(str(e))
            return False
        if self.repo_pin_priority:
            if not self.origin:
                logging.error(
                    "Cannot setup apt pin. Empty apt repo origin value '%s'." %
                    self.origin)
                logging.error(
                    status.MESSAGE_ENABLED_FAILED_TMPL.format(
                        title=self.title))
                return False
            repo_pref_file = self.repo_pref_file_tmpl.format(
                name=self.name, series=series)
            apt.add_ppa_pinning(
                repo_pref_file, repo_url, self.origin, self.repo_pin_priority)
        if not os.path.exists(apt.APT_METHOD_HTTPS_FILE):
            util.subp(['apt-get', 'install', 'apt-transport-https'],
                      capture=True)
        if not os.path.exists(apt.CA_CERTIFICATES_FILE):
            util.subp(['apt-get', 'install', 'ca-certificates'], capture=True)
        try:
            util.subp(['apt-get', 'update'], capture=True)
            if self.packages:
                print(
                    'Installing {title} packages ...'.format(title=self.title))
                util.subp(['apt-get', 'install'] + self.packages, capture=True)
        except util.ProcessExecutionError:
            self.disable(silent=True, force=True)
            logging.error(
                status.MESSAGE_ENABLED_FAILED_TMPL.format(title=self.title))
            return False
        print(status.MESSAGE_ENABLED_TMPL.format(title=self.title))
        for msg in self.messaging.get('post_enable', []):
            print(msg)
        return True

    def operational_status(self):
        """Return operational status of RepoEntitlement."""
        passed_affordances, details = self.check_affordances()
        if not passed_affordances:
            return status.INAPPLICABLE, details
        entitlement_cfg = self.cfg.entitlements.get(self.name)
        if not entitlement_cfg:
            return status.INACTIVE, '%s PPA is not configured' % self.title
        directives = entitlement_cfg['entitlement'].get('directives', {})
        repo_url = directives.get('aptURL')
        if not repo_url:
            repo_url = self.repo_url
        protocol, repo_path = repo_url.split('://')
        apt_repo_file = repo_url.split('://')[1].replace('/', '_')
        if glob.glob('/var/lib/apt/lists/%s*' % apt_repo_file):
            return status.ACTIVE, '%s PPA is active' % self.title
        return status.INACTIVE, '%s PPA is not configured' % self.title
