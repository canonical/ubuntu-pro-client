from typing import Optional  # noqa: F401

from uaclient import messages
from uaclient.entitlements import repo
from uaclient.types import (  # noqa: F401
    MessagingOperations,
    MessagingOperationsDict,
)

CC_README = "/usr/share/doc/ubuntu-commoncriteria/README"


class CommonCriteriaEntitlement(repo.RepoEntitlement):

    help_doc_url = messages.urls.COMMON_CRITERIA_HOME_PAGE
    name = "cc-eal"
    title = messages.CC_TITLE
    description = messages.CC_DESCRIPTION
    help_text = messages.CC_HELP_TEXT
    repo_key_file = "ubuntu-pro-cc-eal.gpg"
    apt_noninteractive = True
    supports_access_only = True
    origin = "UbuntuCC"

    @property
    def messaging(self) -> MessagingOperationsDict:
        post_enable = None  # type: Optional[MessagingOperations]
        if not self.access_only:
            post_enable = [messages.CC_POST_ENABLE.format(filename=CC_README)]
        return {
            "pre_install": [messages.CC_PRE_INSTALL],
            "post_enable": post_enable,
        }
