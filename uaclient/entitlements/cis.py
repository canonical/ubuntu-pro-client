from typing import List

from uaclient.entitlements import repo
from uaclient.types import MessagingOperationsDict

CIS_DOCS_URL = "https://ubuntu.com/security/cis"
USG_DOCS_URL = "https://ubuntu.com/security/certifications/docs/usg"


class CISEntitlement(repo.RepoEntitlement):

    help_doc_url = USG_DOCS_URL
    name = "cis"
    description = "Security compliance and audit tools"
    repo_key_file = "ubuntu-advantage-cis.gpg"
    apt_noninteractive = True
    supports_access_only = True

    @property
    def messaging(self) -> MessagingOperationsDict:
        if self._called_name == "usg":
            return {
                "post_enable": [
                    "Visit {} for the next steps".format(USG_DOCS_URL)
                ]
            }
        messages = {
            "post_enable": [
                "Visit {} to learn how to use CIS".format(CIS_DOCS_URL)
            ]
        }  # type: MessagingOperationsDict
        if "usg" in self.valid_names:
            messages["pre_can_enable"] = [
                "From Ubuntu 20.04 and onwards 'pro enable cis' has been",
                "replaced by 'pro enable usg'. See more information at:",
                USG_DOCS_URL,
            ]
        return messages

    @property
    def packages(self) -> List[str]:
        if self._called_name == "usg":
            return []
        return super().packages

    @property
    def title(self) -> str:
        if self._called_name == "cis":
            return "CIS Audit"
        return "Ubuntu Security Guide"
