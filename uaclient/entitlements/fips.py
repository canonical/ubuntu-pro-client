import os

from uaclient import apt
from uaclient.entitlements import repo
from uaclient import util


class FIPSEntitlement(repo.RepoEntitlement):

    name = 'fips'
    title = 'FIPS'
    description = 'Canonical FIPS 140-2 Certified Modules'
    repo_url = 'https://private-ppa.launchpad.net/ubuntu-advantage/fips'
    repo_key_file = 'ubuntu-fips-keyring.gpg'
    static_affordances = (
        ('Cannot install FIPS on a container', util.is_container, False),)

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
        # TODO(Get credentials from Contract service's Entitlements response)
        credentials = 'user{name}:pass'.format(name=self.name)
        apt.add_auth_apt_repo(
            repo_filename, self.repo_url, credentials, keyring_file)
        if not os.path.exists(apt.APT_METHOD_HTTPS_FILE):
            util.subp(['apt-get', 'install', 'apt-transport-https'],
                      capture=True)
        if not os.path.exists(apt.CA_CERTIFICATES_FILE):
            util.subp(['apt-get', 'install', 'ca-certificates'],
                      capture=True)
        util.subp(['apt-get', 'update'], capture=True)
        print('{title} configured, please reboot to enable.'.format(
            title=self.title))
        return True

    def can_disable(self, silent=False):
        can_disable = super(FIPSEntitlement, self).can_disable(silent)
        if not can_disable:
            return False
        if not silent:
            print('Warning: no option to disable FIPS')
        return False


class FIPSUpdatesEntitlement(repo.RepoEntitlement):

    name = 'fips-updates'
    title = 'FIPS Updates'
    description = 'Canonical FIPS 140-2 Certified Modules'
    repo_url = (
        'https://private-ppa.launchpad.net/ubuntu-advantage/fips-updates')
    repo_key_file = 'ubuntu-fips-updates-keyring.gpg'
    static_affordances = (
        ('Cannot install FIPS Updates on a container',
         util.is_container, False),)

    def enable(self):
        """Enable specific entitlement.

        @return: True on success, False otherwise.
        """
        if not self.can_enable():
            return False
        print('FIPS Updates configured, please reboot to enable.')
        return True

    def can_disable(self, silent=False):
        can_disable = super(FIPSUpdatesEntitlement, self).can_disable(silent)
        if not can_disable:
            return False
        if not silent:
            print('Warning: no option to disable FIPS')
        return False
