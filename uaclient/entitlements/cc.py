from uaclient.entitlements import repo
from uaclient.types import MessagingOperationsDict

CC_README = "/usr/share/doc/ubuntu-commoncriteria/README"


class CommonCriteriaEntitlement(repo.RepoEntitlement):

    help_doc_url = "https://ubuntu.com/cc-eal"
    name = "cc-eal"
    title = "CC EAL2"
    description = "Common Criteria EAL2 Provisioning Packages"
    repo_key_file = "ubuntu-advantage-cc-eal.gpg"
    apt_noninteractive = True

    @property
    def messaging(self) -> MessagingOperationsDict:
        return {
            "pre_install": [
                "(This will download more than 500MB of packages, so may take"
                " some time.)"
            ],
            "post_enable": [
                "Please follow instructions in {} to configure EAL2".format(
                    CC_README
                )
            ],
        }
