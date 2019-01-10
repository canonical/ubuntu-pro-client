import logging
import os

from uaclient import apt
from uaclient.entitlements import repo
from uaclient import status
from uaclient import util


class FIPSCommonEntitlement(repo.RepoEntitlement):

    def enable(self):
        """Enable specific entitlement.

        @return: True on success, False otherwise.
        """
        if not self.can_enable():
            return False
        series = util.get_platform_info('series')
        repo_filename = self.repo_list_file_tmpl.format(
            name=self.name, series=series)
        keyring_file = os.path.join(apt.KEYRINGS_DIR, self.repo_key_file)
        access_directives = self.cfg.read_cache(
            'machine-access-%s' % self.name).get('directives', {})
        token = access_directives.get('token')
        if not token:
            logging.debug(
                'No specific entitlement token present. Using machine token'
                ' as %s credentials', self.title)
            token = self.cfg.machine_token['machineSecret']
        apt.add_auth_apt_repo(
            repo_filename, self.repo_url, token, keyring_file)
        if not os.path.exists(apt.APT_METHOD_HTTPS_FILE):
            util.subp(['apt-get', 'install', 'apt-transport-https'],
                      capture=True)
        if not os.path.exists(apt.CA_CERTIFICATES_FILE):
            util.subp(['apt-get', 'install', 'ca-certificates'],
                      capture=True)
        try:
            util.subp(['apt-get', 'update'], capture=True)
        except util.ProcessExecutionError:
            self.disable(silent=True, force=True)
            logging.error(
                status.MESSAGE_ENABLED_FAILED_TMPL.format(title=self.title))
            return False
        print('{title} configured, please reboot to enable.'.format(
            title=self.title))
        return True

    def disable(self, silent=False, force=False):
        if not self.can_disable(silent, force):
            return False
        if force:  # Force config cleanup as broke during setup attempt.
            series = util.get_platform_info('series')
            repo_filename = self.repo_list_file_tmpl.format(
                name=self.name, series=series)
            keyring_file = os.path.join(apt.APT_KEYS_DIR, self.repo_key_file)
            access_directives = self.cfg.read_cache(
                'machine-access-%s' % self.name).get('directives', {})
            repo_url = access_directives.get('serviceURL', self.repo_url)
            if not repo_url:
                repo_url = self.repo_url
            apt.remove_auth_apt_repo(repo_filename, repo_url, keyring_file)
        if not silent:
            print('Warning: no option to disable {title}'.format(
                      title=self.title))
        return False


class FIPSEntitlement(FIPSCommonEntitlement):

    name = 'fips'
    title = 'FIPS'
    description = 'Canonical FIPS 140-2 Certified Modules'
    repo_url = 'https://private-ppa.launchpad.net/ubuntu-advantage/fips'
    repo_key_file = 'ubuntu-fips-keyring.gpg'
    static_affordances = (
        ('Cannot install FIPS on a container', util.is_container, False),)


class FIPSUpdatesEntitlement(FIPSCommonEntitlement):

    name = 'fips-updates'
    title = 'FIPS Updates'
    description = 'Canonical FIPS 140-2 Certified Modules with Updates'
    repo_url = (
        'https://private-ppa.launchpad.net/ubuntu-advantage/fips-updates')
    repo_key_file = 'ubuntu-fips-updates-keyring.gpg'
    static_affordances = (
        ('Cannot install FIPS Updates on a container',
         util.is_container, False),)
