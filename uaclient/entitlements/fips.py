from uaclient.entitlements import repo
from uaclient import util

try:
    from typing import List  # noqa
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass


class FIPSCommonEntitlement(repo.RepoEntitlement):

    repo_pin_priority = 1001
    fips_required_packages = [
        'openssh-client-hmac', 'openssh-server-hmac', 'libssl1.0.0-hmac',
        'linux-fips', 'strongswan-hmac', 'openssh-client', 'openssh-server',
        'openssl', 'libssl1.0.0', 'fips-initramfs', 'strongswan']
    force_disable = True

    @property
    def packages(self) -> 'List[str]':
        return self.fips_required_packages


class FIPSEntitlement(FIPSCommonEntitlement):

    name = 'fips'
    title = 'FIPS'
    description = 'Canonical FIPS 140-2 Certified Modules'
    messaging = {'post_enable': ['FIPS configured, please reboot to enable.']}
    origin = 'UbuntuFIPS'
    repo_url = 'https://private-ppa.launchpad.net/ubuntu-advantage/fips'
    repo_key_file = 'ubuntu-fips-keyring.gpg'
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
    repo_key_file = 'ubuntu-fips-updates-keyring.gpg'
    static_affordances = (
        ('Cannot install FIPS Updates on a container',
         util.is_container, False),)
