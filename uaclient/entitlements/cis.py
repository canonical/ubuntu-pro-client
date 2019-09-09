from uaclient.entitlements import repo


class CISEntitlement(repo.RepoEntitlement):

    name = "cis-audit"
    title = "CIS Audit"
    description = "Center for Internet Security Audit Tools"
    repo_url = (
        "https://private-ppa.launchpad.net/ubuntu-advantage/"
        "security-benchmarks"
    )
    repo_key_file = "ubuntu-securitybenchmarks-keyring.gpg"
    packages = ["ubuntu-cisbenchmark-16.04"]
