from uaclient.entitlements import repo


class CISEntitlement(repo.RepoEntitlement):

    name = 'cis-audit'
    title = 'Canonical CIS Benchmark Audit Tool'
    description = (
        'Canonical Center for Internet Security Benchmark Audit Tool')
    repo_url = ('https://private-ppa.launchpad.net/ubuntu-advantage/'
                'security-benchmarks')
    repo_key_file = 'ubuntu-securitybenchmarks-keyring.gpg'
    packages = ['ubuntu-cisbenchmark-16.04']
