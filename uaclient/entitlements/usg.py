from uaclient import messages
from uaclient.entitlements import repo
from uaclient.types import MessagingOperationsDict


class USGEntitlement(repo.RepoEntitlement):

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
        return {"post_enable": [messages.USG_POST_ENABLE]}
