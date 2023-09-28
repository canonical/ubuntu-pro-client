from typing import List

from uaclient import messages
from uaclient.entitlements import repo
from uaclient.types import MessagingOperationsDict


class CISEntitlement(repo.RepoEntitlement):

    help_doc_url = messages.urls.USG_DOCS
    name = "cis"
    description = messages.CIS_DESCRIPTION
    help_text = messages.CIS_HELP_TEXT
    repo_key_file = "ubuntu-pro-cis.gpg"
    apt_noninteractive = True
    supports_access_only = True
    origin = "UbuntuCIS"

    @property
    def messaging(self) -> MessagingOperationsDict:
        if self._called_name == "usg":
            return {"post_enable": [messages.CIS_USG_POST_ENABLE]}
        ret = {
            "post_enable": [messages.CIS_POST_ENABLE]
        }  # type: MessagingOperationsDict
        if "usg" in self.valid_names:
            ret["pre_can_enable"] = [messages.CIS_IS_NOW_USG]
        return ret

    @property
    def packages(self) -> List[str]:
        if self._called_name == "usg":
            return []
        return super().packages

    @property
    def title(self) -> str:
        if self._called_name == "cis":
            return messages.CIS_TITLE
        return messages.CIS_USG_TITLE
