from typing import Tuple, Type  # noqa: F401

from uaclient.entitlements import repo
from uaclient.entitlements.base import UAEntitlement


class ROSCommonEntitlement(repo.RepoEntitlement):
    help_doc_url = "https://ubuntu.com/robotics/ros-esm"
    repo_key_file = "ubuntu-pro-ros.gpg"


class ROSEntitlement(ROSCommonEntitlement):
    name = "ros"
    title = "ROS ESM Security Updates"
    description = "Security Updates for the Robot Operating System"
    help_text = """\
ros provides access to a private PPA which includes security-related updates
for available high and critical CVE fixes for Robot Operating System (ROS)
packages. For access to ROS ESM and security updates, both esm-infra and
esm-apps services will also be enabled. To get additional non-security updates,
enable ros-updates. You can find out more about the ROS ESM service at
https://ubuntu.com/robotics/ros-esm"""

    @property
    def required_services(self) -> Tuple[Type[UAEntitlement], ...]:
        from uaclient.entitlements.esm import (
            ESMAppsEntitlement,
            ESMInfraEntitlement,
        )

        return (
            ESMInfraEntitlement,
            ESMAppsEntitlement,
        )

    @property
    def dependent_services(self) -> Tuple[Type[UAEntitlement], ...]:
        return (ROSUpdatesEntitlement,)


class ROSUpdatesEntitlement(ROSCommonEntitlement):
    name = "ros-updates"
    title = "ROS ESM All Updates"
    description = "All Updates for the Robot Operating System"
    help_text = """\
ros-updates provides access to a private PPA that includes non-security-related
updates for Robot Operating System (ROS) packages. For full access to ROS ESM,
security and non-security updates, the esm-infra, esm-apps, and ros services
will also be enabled. You can find out more about the ROS ESM service at
https://ubuntu.com/robotics/ros-esm"""

    @property
    def required_services(self) -> Tuple[Type[UAEntitlement], ...]:
        from uaclient.entitlements.esm import (
            ESMAppsEntitlement,
            ESMInfraEntitlement,
        )

        return (
            ESMInfraEntitlement,
            ESMAppsEntitlement,
            ROSEntitlement,
        )
