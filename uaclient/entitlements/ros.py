from typing import Tuple  # noqa: F401

from uaclient.entitlements import repo


class ROSESMEntitlement(repo.RepoEntitlement):
    help_doc_url = ""
    name = "esm-ros"
    title = "ROS ESM"
    description = "ROS ESM Service"
    repo_key_file = "ubuntu-advantage-esm-ros.gpg"
    is_beta = True
    _required_services = ("esm-infra", "esm-apps")  # type: Tuple[str, ...]
