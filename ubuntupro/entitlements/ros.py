from typing import Tuple, Type  # noqa: F401

from ubuntupro.entitlements import repo
from ubuntupro.entitlements.base import UAEntitlement


class ROSCommonEntitlement(repo.RepoEntitlement):
    help_doc_url = "https://ubuntu.com/robotics/ros-esm"
    repo_key_file = "ubuntu-pro-ros.gpg"


class ROSEntitlement(ROSCommonEntitlement):
    name = "ros"
    title = "ROS ESM Security Updates"
    description = "Security Updates for the Robot Operating System"

    @property
    def required_services(self) -> Tuple[Type[UAEntitlement], ...]:
        from ubuntupro.entitlements.esm import (
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

    @property
    def required_services(self) -> Tuple[Type[UAEntitlement], ...]:
        from ubuntupro.entitlements.esm import (
            ESMAppsEntitlement,
            ESMInfraEntitlement,
        )

        return (
            ESMInfraEntitlement,
            ESMAppsEntitlement,
            ROSEntitlement,
        )
