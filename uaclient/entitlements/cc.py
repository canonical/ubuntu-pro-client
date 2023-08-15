from typing import Optional  # noqa: F401

from uaclient.entitlements import repo
from uaclient.types import (  # noqa: F401
    MessagingOperations,
    MessagingOperationsDict,
)

CC_README = "/usr/share/doc/ubuntu-commoncriteria/README"


class CommonCriteriaEntitlement(repo.RepoEntitlement):

    help_doc_url = "https://ubuntu.com/cc-eal"
    name = "cc-eal"
    title = "CC EAL2"
    description = "Common Criteria EAL2 Provisioning Packages"
    help_text = """\
Common Criteria is an Information Technology Security Evaluation standard
(ISO/IEC IS 15408) for computer security certification. Ubuntu 16.04 has been
evaluated to assurance level EAL2 through CSEC. The evaluation was performed
on Intel x86_64, IBM Power8 and IBM Z hardware platforms."""
    repo_key_file = "ubuntu-pro-cc-eal.gpg"
    apt_noninteractive = True
    supports_access_only = True

    @property
    def messaging(self) -> MessagingOperationsDict:
        post_enable = None  # type: Optional[MessagingOperations]
        if not self.access_only:
            post_enable = [
                "Please follow instructions in {} to configure EAL2".format(
                    CC_README
                )
            ]
        return {
            "pre_install": [
                "(This will download more than 500MB of packages, so may take"
                " some time.)"
            ],
            "post_enable": post_enable,
        }
