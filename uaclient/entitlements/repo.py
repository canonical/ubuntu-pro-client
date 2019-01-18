import glob
import logging
import os
import platform

from uaclient import apt
from uaclient.entitlements import base
from uaclient import status
from uaclient import util


class RepoEntitlement(base.UAEntitlement):

    repo_list_file_tmpl = '/etc/apt/sources.list.d/ubuntu-{name}-{series}.list'
    repo_pref_file_tmpl = '/etc/apt/preferences.d/ubuntu-{name}-{series}'

    # TODO(Get serviceURL from Contract service's Entitlements response)
    # https://github.com/CanonicalLtd/ua-service/issues/7
    # Set by subclasses
    repo_url = 'UNSET'
    repo_key_file = 'UNSET'  # keyfile delivered by ubuntu-cloudimage-keyring
    repo_pin_priority = None      # Optional repo pin priority in subclass

    def enable(self):
        """Enable specific entitlement.

        @return: True on success, False otherwise.
        """
        if not self.can_enable():
            return False
        series = platform.dist()[2]
        repo_filename = self.repo_list_file_tmpl.format(
            name=self.name, series=series)
        # TODO(Contract service needs to commit to a token directive)
        access_directives = self.cfg.read_cache(
            'machine-access-%s' % self.name).get('directives', {})
        token = access_directives.get('legacyBasicAuth')
        if not token:
            logging.debug(
                'No legacy entitlement token present. Using machine token'
                ' as %s credentials', self.title)
            token = self.cfg.machine_token['machineSecret']
        ppa_fingerprint = access_directives.get('aptKey')
        if ppa_fingerprint:
            keyring_file = None
        else:
            keyring_file = os.path.join(apt.KEYRINGS_DIR, self.repo_key_file)
        repo_url = access_directives.get('serviceURL')
        if not repo_url:
            repo_url = self.repo_url
        try:
            apt.add_auth_apt_repo(
                repo_filename, repo_url, token, keyring_file, ppa_fingerprint)
        except apt.InvalidAPTCredentialsError as e:
            logging.error(str(e))
            return False
        if self.repo_pin_priority:
            repo_pref_file = self.repo_pref_file_tmpl.format(
                name=self.name, series=series)
            apt.add_ppa_pinning(
                repo_pref_file, repo_url, self.repo_pin_priority)
        if not os.path.exists(apt.APT_METHOD_HTTPS_FILE):
            util.subp(['apt-get', 'install', 'apt-transport-https'],
                      capture=True)
        if not os.path.exists(apt.CA_CERTIFICATES_FILE):
            util.subp(['apt-get', 'install', 'ca-certificates'], capture=True)
        try:
            util.subp(['apt-get', 'update'], capture=True)
        except util.ProcessExecutionError:
            self.disable(silent=True, force=True)
            logging.error(
                status.MESSAGE_ENABLED_FAILED_TMPL.format(title=self.title))
            return False
        print(status.MESSAGE_ENABLED_TMPL.format(title=self.title))
        return True

    def operational_status(self):
        """Return operational status of RepoEntitlement."""
        passed_affordances, details = self.check_affordances()
        if not passed_affordances:
            return status.INAPPLICABLE, details
        apt_policy, _err = util.subp(['apt-cache', 'policy'])
        access_directives = self.cfg.read_cache(
            'machine-access-%s' % self.name).get('directives', {})
        repo_url = access_directives.get('serviceURL')
        if not repo_url:
            repo_url = self.repo_url
        protocol, repo_path = repo_url.split('://')
        apt_repo_file = repo_url.split('://')[1].replace('/', '_')
        if glob.glob('/var/lib/apt/lists/%s*' % apt_repo_file):
            return status.ACTIVE, '%s PPA is active' % self.title
        return status.INACTIVE, '%s PPA is not configured' % self.title
