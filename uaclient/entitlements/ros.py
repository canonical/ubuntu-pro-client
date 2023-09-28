from typing import Tuple, Type  # noqa: F401

from uaclient import messages
from uaclient.entitlements import repo
from uaclient.entitlements.base import UAEntitlement


class ROSCommonEntitlement(repo.RepoEntitlement):
    help_doc_url = messages.urls.ROS_HOME_PAGE
    repo_key_file = "ubuntu-pro-ros.gpg"


class ROSEntitlement(ROSCommonEntitlement):
    name = "ros"
    title = messages.ROS_TITLE
    description = messages.ROS_DESCRIPTION
    help_text = messages.ROS_HELP_TEXT
    origin = "UbuntuROS"

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
    title = messages.ROS_UPDATES_TITLE
    description = messages.ROS_UPDATES_DESCRIPTION
    help_text = messages.ROS_UPDATES_HELP_TEXT
    origin = "UbuntuROSUpdates"

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
