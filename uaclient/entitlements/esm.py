from uaclient.entitlements import repo


class ESMEntitlement(repo.RepoEntitlement):

    name = 'esm'
    title = 'Extended Security Maintenance'
    origin = 'UbuntuESM'
    description = (
        'Ubuntu Extended Security Maintenance archive'
        ' (https://ubuntu.com/esm)')
    repo_url = 'https://esm.ubuntu.com'
    repo_key_file = 'ubuntu-esm-v2-keyring.gpg'
    repo_pin_priority = 'never'
    disable_apt_auth_only = True  # Only remove apt auth files when disabling
