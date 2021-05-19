from uaclient.entitlements import repo

try:
    from typing import Callable, Dict, List, Tuple, Union  # noqa
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass

CIS_DOCS_URL = "https://security-certs.docs.ubuntu.com/en/cis"


class CISEntitlement(repo.RepoEntitlement):

    help_doc_url = "https://ubuntu.com/security/certifications#cis"
    name = "cis"
    title = "CIS Audit"
    description = "Center for Internet Security Audit Tools"
    repo_key_file = "ubuntu-advantage-cis.gpg"
    apt_noninteractive = True

    @property
    def messaging(
        self,
    ) -> "Dict[str, List[Union[str, Tuple[Callable, Dict]]]]":
        return {
            "post_enable": [
                "Visit {} to learn how to use CIS".format(CIS_DOCS_URL)
            ]
        }
