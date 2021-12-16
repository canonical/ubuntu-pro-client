from typing import Callable, Dict, List, Tuple, Union

from uaclient.entitlements import repo

CIS_DOCS_URL = "https://ubuntu.com/security/certifications/docs/cis"
USG_DOCS_URL = "https://ubuntu.com/security/certifications/docs/cis"


class CISEntitlement(repo.RepoEntitlement):

    help_doc_url = "https://ubuntu.com/security/certifications#cis"
    name = "cis"
    title = "CIS Audit"
    description = "Center for Internet Security Audit Tools"
    repo_key_file = "ubuntu-advantage-cis.gpg"
    apt_noninteractive = True

    @property
    def messaging(self,) -> Dict[str, List[Union[str, Tuple[Callable, Dict]]]]:
        if self._called_name == "usg":
            return {
                "post_enable": [
                    "Visit {} for the next steps on USG".format(USG_DOCS_URL)
                ]
            }
        messages = {
            "post_enable": [
                "Visit {} to learn how to use CIS".format(CIS_DOCS_URL)
            ]
        }  # type: Dict[str, List[Union[str, Tuple[Callable, Dict]]]]
        if "usg" in self.valid_names:
            messages["pre_enable"] = [
                "From Ubuntu 20.04, 'ua enable cis' is deprecated.",
                "Consider running 'ua enable usg' and then"
                " 'apt-get install usg-cisbenchmark",
                "to get the CIS audit package.",
                "Enabling USG instead.",
            ]
        return messages

    @property
    def packages(self) -> List[str]:
        if self._called_name == "usg":
            return []
        return super().packages
