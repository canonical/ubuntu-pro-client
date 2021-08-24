from typing import Tuple  # noqa: F401

from uaclient.entitlements import repo


class ROSESMEntitlement(repo.RepoEntitlement):
    help_doc_url = "https://ubuntu.com/robotics/ros-esm"
    name = "esm-ros"
    title = "ROS ESM"
    description = "ROS Extended Security Maintenance (ESM)"
    repo_key_file = "ubuntu-advantage-esm-ros.gpg"
    is_beta = True
    _required_services = ("esm-infra", "esm-apps")  # type: Tuple[str, ...]
