from uaclient.entitlements import repo


class CISEntitlement(repo.RepoEntitlement):

    help_doc_url = "https://ubuntu.com/cis-audit"
    name = "cis-audit"
    title = "CIS Audit"
    description = "Center for Internet Security Audit Tools"
    repo_key_file = "ubuntu-securitybenchmarks-keyring.gpg"
    packages = ["ubuntu-cisbenchmark-16.04"]
