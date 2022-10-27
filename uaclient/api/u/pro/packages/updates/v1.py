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
    filter_security_updates,
    get_installed_packages_by_origin,
    get_ua_info,
)


class UpdateSummary(DataObject):
    fields = [
        Field("num_updates", IntDataValue),
        Field("num_esm_apps_updates", IntDataValue),
        Field("num_esm_infra_updates", IntDataValue),
        Field("num_standard_security_updates", IntDataValue),
        Field("num_standard_updates", IntDataValue),
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
        Field("download_size", IntDataValue),
        Field("origin", StringDataValue),
        Field("package", StringDataValue),
        Field("provided_by", StringDataValue),
        Field("status", StringDataValue),
        Field("version", StringDataValue),
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
        Field("summary", UpdateSummary),
        Field("updates", data_list(UpdateInfo)),
    ]

    def __init__(self, summary: UpdateSummary, updates: List[UpdateInfo]):
        self.summary = summary
        self.updates = updates


def updates() -> PackageUpdatesResult:
    return _updates(UAConfig())


def _updates(cfg: UAConfig) -> PackageUpdatesResult:
    ua_info = get_ua_info(cfg)
    packages = get_installed_packages_by_origin()
    upgradable_versions = filter_security_updates(packages["all"])
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
