from typing import List

from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UAConfig
from uaclient.data_types import (
    DataObject,
    Field,
    IntDataValue,
    StringDataValue,
    data_list,
)
from uaclient.security_status import (
    create_updates_list,
    filter_updates,
    get_installed_packages_by_origin,
    get_ua_info,
)


class UpdateSummary(DataObject):
    fields = [
        Field(
            "num_updates", IntDataValue, doc="Total count of available updates"
        ),
        Field(
            "num_esm_apps_updates",
            IntDataValue,
            doc="Count of available updates from ``esm-apps``",
        ),
        Field(
            "num_esm_infra_updates",
            IntDataValue,
            doc="Count of available updates from ``esm-infra``",
        ),
        Field(
            "num_standard_security_updates",
            IntDataValue,
            doc="Count of available updates from the ``-security`` pocket",
        ),
        Field(
            "num_standard_updates",
            IntDataValue,
            doc="Count of available updates from the ``-updates`` pocket",
        ),
    ]

    def __init__(
        self,
        num_updates: int,
        num_esm_apps_updates: int,
        num_esm_infra_updates: int,
        num_standard_security_updates: int,
        num_standard_updates: int,
    ):
        self.num_updates = num_updates
        self.num_esm_apps_updates = num_esm_apps_updates
        self.num_esm_infra_updates = num_esm_infra_updates
        self.num_standard_security_updates = num_standard_security_updates
        self.num_standard_updates = num_standard_updates


class UpdateInfo(DataObject):
    fields = [
        Field(
            "download_size",
            IntDataValue,
            doc="Download size for the update in bytes",
        ),
        Field(
            "origin",
            StringDataValue,
            doc="Where the update is downloaded from",
        ),
        Field(
            "package", StringDataValue, doc="Name of the package to be updated"
        ),
        Field(
            "provided_by",
            StringDataValue,
            doc="Service which provides the update",
        ),
        Field(
            "status",
            StringDataValue,
            doc="Whether this update is ready for download or not",
        ),
        Field("version", StringDataValue, doc="Version of the update"),
    ]

    def __init__(
        self,
        download_size: int,
        origin: str,
        package: str,
        provided_by: str,
        status: str,
        version: str,
    ):
        self.download_size = download_size
        self.origin = origin
        self.package = package
        self.provided_by = provided_by
        self.status = status
        self.version = version


class PackageUpdatesResult(DataObject, AdditionalInfo):
    fields = [
        Field(
            "summary", UpdateSummary, doc="Summary of all available updates"
        ),
        Field(
            "updates",
            data_list(UpdateInfo),
            doc="Detailed list of all available updates",
        ),
    ]

    def __init__(self, summary: UpdateSummary, updates: List[UpdateInfo]):
        self.summary = summary
        self.updates = updates


def updates() -> PackageUpdatesResult:
    return _updates(UAConfig())


def _updates(cfg: UAConfig) -> PackageUpdatesResult:
    """
    This endpoint shows available updates for packages in a system, categorised
    by where they can be obtained.
    """
    ua_info = get_ua_info(cfg)
    packages = get_installed_packages_by_origin()
    upgradable_versions = filter_updates(packages["all"])
    update_list = create_updates_list(upgradable_versions, ua_info)

    num_esm_apps_updates = len(upgradable_versions["esm-apps"])
    num_esm_infra_updates = len(upgradable_versions["esm-infra"])
    num_standard_security_updates = len(
        upgradable_versions["standard-security"]
    )
    num_standard_updates = len(upgradable_versions["standard-updates"])

    summary = UpdateSummary(
        num_updates=num_esm_apps_updates
        + num_esm_infra_updates
        + num_standard_security_updates
        + num_standard_updates,
        num_esm_apps_updates=num_esm_apps_updates,
        num_esm_infra_updates=num_esm_infra_updates,
        num_standard_security_updates=num_standard_security_updates,
        num_standard_updates=num_standard_updates,
    )
    updates = [
        UpdateInfo(
            download_size=update["download_size"],
            origin=update["origin"],
            package=update["package"],
            provided_by=update["service_name"],
            status=update["status"],
            version=update["version"],
        )
        for update in update_list
    ]

    return PackageUpdatesResult(summary=summary, updates=updates)


endpoint = APIEndpoint(
    version="v1",
    name="PackageUpdates",
    fn=_updates,
    options_cls=None,
)

_doc = {
    "introduced_in": "27.12",
    "requires_network": False,
    "example_python": """
from uaclient.api.u.pro.packages.updates.v1 import updates

result = updates()
""",  # noqa: E501
    "result_class": PackageUpdatesResult,
    "exceptions": [],
    "example_cli": "pro api u.pro.packages.updates.v1",
    "example_json": """
{
    "summary": {
        "num_updates": 1,
        "num_esm_apps_updates": 2,
        "num_esm_infra_updates": 3,
        "num_standard_security_updates": 4,
        "num_standard_updates": 5,
    },
    "updates": [
        {
            "download_size": 6,
            "origin": "<some site>",
            "package": "<package name>",
            "provided_by": "<service name>",
            "status": "<update status>",
            "version": "<updated version>",
        },
    ]
}
""",
}
