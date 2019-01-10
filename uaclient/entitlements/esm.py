import os

from uaclient import apt
from uaclient.entitlements import repo
from uaclient import status
from uaclient import util


class ESMEntitlement(repo.RepoEntitlement):

    name = 'esm'
    title = 'Extended Security Maintenance'
    description = (
        'Ubuntu Extended Security Maintenance archive'
        ' (https://ubuntu.com/esm)')
    repo_url = 'https://esm.ubuntu.com'
    repo_key_file = 'ubuntu-esm-keyring.gpg'

    def disable(self, silent=False, force=False):
        """Disable specific entitlement

        @return: True on success, False otherwise.
        """
        if not self.can_disable(silent, force):
            return False
        series = util.get_platform_info('series')
        repo_filename = self.repo_list_file_tmpl.format(
            name=self.name, series=series)
        keyring_file = os.path.join(apt.APT_KEYS_DIR, self.repo_key_file)
        access_directives = self.cfg.read_cache(
            'machine-access-%s' % self.name).get('directives', {})
        repo_url = access_directives.get('repo_url', self.repo_url)
        if not repo_url:
            repo_url = self.repo_url
        apt.remove_auth_apt_repo(repo_filename, repo_url, keyring_file)
        print(status.MESSAGE_DISABLED_TMPL.format(title=self.title))
        return True
