from uaclient.entitlements import repo


class ESMEntitlement(repo.RepoEntitlement):

    help_doc_url = "https://ubuntu.com/esm"
    name = "esm-infra"
    title = "ESM Infra"
    origin = "UbuntuESM"
    description = "UA Infra: Extended Security Maintenance"
    repo_url = "https://esm.ubuntu.com"
    repo_key_file = "ubuntu-advantage-esm-infra-trusty.gpg"
    repo_pin_priority = "never"
    disable_apt_auth_only = True  # Only remove apt auth files when disabling


class ESMLegacyEntitlement(repo.RepoEntitlement):

    help_doc_url = "https://ubuntu.com/esm"
    name = "esm-infra-legacy"
    title = "Ubuntu Pro: ESM Infra (Legacy)"
    origin = "UbuntuESM"
    description = "Expanded Security Maintenance for Infrastructure on Legacy Instances"  # noqa
    repo_url = "https://esm.ubuntu.com/infra-legacy/"
    repo_key_file = "ubuntu-advantage-esm-infra-trusty.gpg"
    disable_apt_auth_only = False
