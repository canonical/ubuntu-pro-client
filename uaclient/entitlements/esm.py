from uaclient.entitlements import repo


class ESMInfraEntitlement(repo.RepoEntitlement):

    help_doc_url = "https://ubuntu.com/esm"
    name = "esm-infra"
    title = "ESM Infra"
    origin = "UbuntuESM"
    description = "UA Infra: Extended Security Maintenance"
    repo_url = "https://esm.ubuntu.com"
    repo_key_file = "ubuntu-advantage-esm-infra-trusty.gpg"
    repo_pin_priority = "never"
    disable_apt_auth_only = True  # Only remove apt auth files when disabling
