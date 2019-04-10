import os

from uaclient import apt
from uaclient.entitlements import repo
from uaclient import util


class FIPSCommonEntitlement(repo.RepoEntitlement):

    repo_pin_priority = 1001
    packages = ['openssh-client-hmac', 'openssh-server-hmac',
                'libssl1.0.0-hmac', 'linux-fips', 'strongswan-hmac',
                'openssh-client', 'openssh-server', 'openssl', 'libssl1.0.0',
                'fips-initramfs', 'strongswan']

    def disable(self, silent=False, force=False):
        if not self.can_disable(silent, force):
            return False
        if force:  # Force config cleanup as broke during setup attempt.
            series = util.get_platform_info('series')
            repo_filename = self.repo_list_file_tmpl.format(
                name=self.name, series=series)
            entitlement = self.cfg.read_cache(
                'machine-access-%s' % self.name).get('entitlement', {})
            access_directives = entitlement.get('directives', {})
            repo_url = access_directives.get('aptURL', self.repo_url)
            if not repo_url:
                repo_url = self.repo_url
            fingerprint = access_directives.get('aptKey')
            apt.remove_auth_apt_repo(repo_filename, repo_url, fingerprint)
            if self.repo_pin_priority:
                repo_pref_file = self.repo_pref_file_tmpl.format(
                    name=self.name, series=series)
                if os.path.exists(repo_pref_file):
                    os.unlink(repo_pref_file)
            apt.remove_apt_list_files(repo_url, series)
            try:
                util.subp(
                    ['apt-get', 'remove', '--assume-yes'] + self.packages)
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
    description = 'Canonical FIPS 140-2 Certified Modules'
    messaging = {'post_enable': ['FIPS configured, please reboot to enable.']}
    origin = 'UbuntuFIPS'
    repo_url = 'https://private-ppa.launchpad.net/ubuntu-advantage/fips'
    static_affordances = (
        ('Cannot install FIPS on a container', util.is_container, False),)


class FIPSUpdatesEntitlement(FIPSCommonEntitlement):

    name = 'fips-updates'
    title = 'FIPS Updates'
    messaging = {'post_enable': [
        'FIPS Updates configured, please reboot to enable.']}
    origin = 'UbuntuFIPSUpdates'
    description = 'Canonical FIPS 140-2 Certified Modules with Updates'
    repo_url = (
        'https://private-ppa.launchpad.net/ubuntu-advantage/fips-updates')
    static_affordances = (
        ('Cannot install FIPS Updates on a container',
         util.is_container, False),)
