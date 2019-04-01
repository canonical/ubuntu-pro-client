import logging
import os

from uaclient import apt
from uaclient.entitlements import repo
from uaclient import status
from uaclient import util


class FIPSCommonEntitlement(repo.RepoEntitlement):

    repo_pin_priority = 1001
    packages = ['openssh-client-hmac', 'openssh-server-hmac',
                'libssl1.0.0-hmac', 'linux-fips strongswan-hmac',
                'openssh-client', 'openssh-server', 'openssl', 'libssl1.0.0',
                'fips-initramfs', 'strongswan']

    def enable(self):
        """Enable specific entitlement.

        @return: True on success, False otherwise.
        """
        if not self.can_enable():
            return False
        series = util.get_platform_info('series')
        repo_filename = self.repo_list_file_tmpl.format(
            name=self.name, series=series)
        resource_cfg = self.cfg.read_cache('machine-access-%s' % self.name)
        access_directives = resource_cfg['entitlement'].get('directives', {})
        ppa_fingerprint = access_directives.get('aptKey')
        if ppa_fingerprint:
            keyring_file = None
        else:
            keyring_file = os.path.join(apt.KEYRINGS_DIR, self.repo_key_file)
        token = resource_cfg.get('resourceToken')
        if not token:
            logging.debug(
                'No legacy entitlement token present. Using machine token'
                ' as %s credentials', self.title)
            token = self.cfg.machine_token['machineSecret']
        repo_url = access_directives.get('aptURL', self.repo_url)
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
                repo_pref_file, repo_url, self.origin, self.repo_pin_priority)
        return True
        if not os.path.exists(apt.APT_METHOD_HTTPS_FILE):
            util.subp(['apt-get', 'install', 'apt-transport-https'],
                      capture=True)
        if not os.path.exists(apt.CA_CERTIFICATES_FILE):
            util.subp(['apt-get', 'install', 'ca-certificates'],
                      capture=True)
        print('Installing {title} packages (this may take a while)'.format(
            title=self.title)
        )
        try:
            util.subp(['apt-get', 'update'], capture=True)
            util.subp(['apt-get', 'install'] + self.packages)
        except util.ProcessExecutionError:
            self.disable(silent=True, force=True)
            logging.error(
                status.MESSAGE_ENABLED_FAILED_TMPL.format(title=self.title))
            return False
        print(status.MESSAGE_ENABLED_TMPL.format(title=self.title))
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
            repo_url = access_directives.get('aptURL', self.repo_url)
            if not repo_url:
                repo_url = self.repo_url
            apt.remove_auth_apt_repo(repo_filename, repo_url, keyring_file)
            if self.repo_pin_priority:
                repo_pref_file = self.repo_pref_file_tmpl.format(
                    name=self.name, series=series)
                if os.path.exists(repo_pref_file):
                    os.unlink(repo_pref_file)
            try:
                util.subp(['apt-get', 'remove', '--frontend=noninteractive',
                           '--assume-yes'] + self.packages)
            except util.ProcessExecutionError:
                pass
        if not silent:
            print('Warning: no option to disable {title}'.format(
                title=self.title)
            )
        return False


class FIPSEntitlement(FIPSCommonEntitlement):

    name = 'fips'
    title = 'FIPS'
    origin = 'UbuntuFIPS'
    description = 'Canonical FIPS 140-2 Certified Modules'
    repo_url = 'https://private-ppa.launchpad.net/ubuntu-advantage/fips'
    repo_key_file = 'ubuntu-fips-keyring.gpg'
    static_affordances = (
        ('Cannot install FIPS on a container', util.is_container, False),)


class FIPSUpdatesEntitlement(FIPSCommonEntitlement):

    name = 'fips-updates'
    title = 'FIPS Updates'
    origin = 'UbuntuFIPSUpdates'
    description = 'Canonical FIPS 140-2 Certified Modules with Updates'
    repo_url = (
        'https://private-ppa.launchpad.net/ubuntu-advantage/fips-updates')
    repo_key_file = 'ubuntu-fips-updates-keyring.gpg'
    static_affordances = (
        ('Cannot install FIPS Updates on a container',
         util.is_container, False),)
