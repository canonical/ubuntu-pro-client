from typing import List, Optional  # noqa: F401

from uaclient import messages
from uaclient.entitlements import repo
from uaclient.entitlements.cis import CISEntitlement
from uaclient.types import (  # noqa: F401
    MessagingOperations,
    MessagingOperationsDict,
)


class USGEntitlement(repo.RepoEntitlement):
    cis_version = False
    help_doc_url = messages.urls.USG_DOCS
    name = "usg"
    title = messages.USG_TITLE
    description = messages.CIS_USG_DESCRIPTION
    help_text = messages.CIS_USG_HELP_TEXT
    repo_key_file = "ubuntu-pro-cis.gpg"
    apt_noninteractive = True
    supports_access_only = True
    origin = "UbuntuCIS"

    @property
    def messaging(self) -> MessagingOperationsDict:
        pre_enable = None  # type: Optional[MessagingOperations]
        if self.cis_version:
            pre_enable = [messages.CIS_IS_NOW_USG]
        return {
            "pre_enable": pre_enable,
            "post_enable": [messages.USG_POST_ENABLE],
        }

    @property
    def packages(self) -> List[str]:
        if self.cis_version:
            return CISEntitlement().packages
        return super().packages
