from uaclient import apt
from uaclient.entitlements import repo
from uaclient import util


class CISEntitlement(repo.RepoEntitlement):

    name = 'cis-audit'
    title = 'Canonical CIS Benchmark Audit Tool'
    description = (
        'Canonical Center for Internet Security Benchmark Audit Tool')
    repo_url = ('https://private-ppa.launchpad.net/ubuntu-advantage/'
                'security-benchmarks')
    packages = ['ubuntu-cisbenchmark-16.04']

    def disable(self, silent=False, force=False):
        """Disable specific entitlement

        @return: True on success, False otherwise.
        """
        if not self.can_disable(silent, force):
            return False
        series = util.get_platform_info('series')
        repo_filename = self.repo_list_file_tmpl.format(
            name=self.name, series=series)
        entitlement_cfg = self.cfg.read_cache(
            'machine-access-%s' % self.name)['entitlement']
        access_directives = entitlement_cfg.get('directives', {})
        repo_url = access_directives.get('aptURL', self.repo_url)
        if not repo_url:
            repo_url = self.repo_url
        fingerprint = access_directives.get('aptKey')
        apt.remove_auth_apt_repo(repo_filename, repo_url, fingerprint)
        apt.remove_apt_list_files(repo_url, series)
        print('Removing packages: %s' % ', '.join(self.packages))
        try:
            util.subp(['apt-get', 'remove', '--assume-yes'] + self.packages)
        except util.ProcessExecutionError:
            pass
        return True
