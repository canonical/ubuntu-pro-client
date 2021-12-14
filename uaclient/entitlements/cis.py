from typing import Callable, Dict, List, Tuple, Union

from uaclient.entitlements import repo
from uaclient.util import get_platform_info

CIS_DOCS_URL = "https://ubuntu.com/security/certifications/docs/cis"
USG_DOCS_URL = "https://ubuntu.com/security/certifications/docs/usg"
USG_NOT_SUPPORTED_SERIES = ("xenial", "bionic")


class CISEntitlement(repo.RepoEntitlement):

    help_doc_url = "https://ubuntu.com/security/certifications#cis"
    name = "cis"
    title = "CIS Audit"
    description = "Center for Internet Security Audit Tools"
    repo_key_file = "ubuntu-advantage-cis.gpg"
    apt_noninteractive = True

    @property
    def messaging(self,) -> Dict[str, List[Union[str, Tuple[Callable, Dict]]]]:
        return {
            "post_enable": [
                "Visit {} to learn how to use CIS".format(CIS_DOCS_URL)
            ]
        }


class USGEntitlement(repo.RepoEntitlement):

    help_doc_url = USG_DOCS_URL
    name = "usg"
    title = "Ubuntu Security Guides"
    description = "Security Audit Tools and Guides"
    repo_key_file = "ubuntu-advantage-cis.gpg"
    apt_noninteractive = True

    @property
    def messaging(self,) -> Dict[str, List[Union[str, Tuple[Callable, Dict]]]]:
        return {
            "post_enable": [
                "Visit {} for the next steps.".format(USG_DOCS_URL)
            ]
        }


def get_cis_usg_entitlement():
    series = get_platform_info()["series"]
    if series in USG_NOT_SUPPORTED_SERIES:
        return CISEntitlement
    return USGEntitlement
