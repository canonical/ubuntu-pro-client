from uaclient.entitlements import repo

CC_README = '/usr/share/doc/ubuntu-commoncriteria/README'


class CommonCriteriaEntitlement(repo.RepoEntitlement):

    name = 'cc-eal'
    title = 'Canonical Common Criteria EAL2 Provisioning'
    description = (
        'Common Criteria for Information Technology Security Evaluation - EAL2'
    )
    repo_url = ('https://private-ppa.launchpad.net/ubuntu-advantage/'
                'commoncriteria')
    repo_key_file = 'ubuntu-cc-keyring.gpg'
    packages = ['ubuntu-commoncriteria']
    messaging = {
        'pre_install': [
            '(This will download more than 500MB of packages, so may take some'
            ' time.)'],
        'post_enable': [
            'Please follow instructions in %s to configure EAL2' % CC_README]}
