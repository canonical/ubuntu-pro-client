from typing import Tuple  # noqa: F401

from uaclient.entitlements import repo


class ROSCommonEntitlement(repo.RepoEntitlement):
    help_doc_url = "https://ubuntu.com/robotics/ros-esm"
    repo_key_file = "ubuntu-advantage-ros.gpg"
    is_beta = True


class ROSEntitlement(ROSCommonEntitlement):
    name = "ros"
    title = "ROS ESM Security Updates"
    description = "Security Updates for the Robot Operating System"
    _required_services = ("esm-infra", "esm-apps")  # type: Tuple[str, ...]
    _dependent_services = ("ros-updates",)  # type: Tuple[str, ...]


class ROSUpdatesEntitlement(ROSCommonEntitlement):
    name = "ros-updates"
    title = "ROS ESM All Updates"
    description = "All Updates for the Robot Operating System"
    _required_services = (
        "esm-infra",
        "esm-apps",
        "ros",
    )  # type: Tuple[str, ...]
