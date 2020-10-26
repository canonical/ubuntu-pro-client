from uaclient.entitlements import repo


class CISEntitlement(repo.RepoEntitlement):

    help_doc_url = "https://ubuntu.com/security/certifications#cis"
    name = "cis-audit"
    title = "CIS Audit"
    description = "Center for Internet Security Audit Tools"
    repo_key_file = "ubuntu-securitybenchmarks-keyring.gpg"
    is_beta = True
