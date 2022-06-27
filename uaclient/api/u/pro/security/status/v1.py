from collections import defaultdict
from typing import Any, DefaultDict, List

from uaclient.config import UAConfig
from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    Field,
    IntDataValue,
    StringDataValue,
    data_list,
)
from uaclient.security_status import (
    filter_security_updates,
    get_installed_packages,
    get_origin_for_package,
    get_service_name,
    get_ua_info,
    get_update_status,
)


class SecurityStatusPackageUpdate(DataObject):
    fields = [
        Field("package", StringDataValue),
        Field("version", StringDataValue),
        Field("service_name", StringDataValue),
        Field("origin", StringDataValue),
        Field("status", StringDataValue),
        Field("download_size", IntDataValue),
    ]

    def __init__(
        self,
        package: str,
        version: str,
        service_name: str,
        origin: str,
        status: str,
        download_size: int,
    ):
        self.package = package
        self.version = version
        self.service_name = service_name
        self.origin = origin
        self.status = status
        self.download_size = download_size


class SecurityStatusSummaryUA(DataObject):
    fields = [
        Field("attached", BoolDataValue),
        Field("enabled_services", data_list(StringDataValue)),
        Field("entitled_services", data_list(StringDataValue)),
    ]

    def __init__(
        self,
        attached: bool,
        enabled_services: List[str],
        entitled_services: List[str],
    ):
        self.attached = attached
        self.enabled_services = enabled_services
        self.entitled_services = entitled_services


class SecurityStatusSummary(DataObject):
    fields = [
        Field("ua", SecurityStatusSummaryUA),
        Field("num_installed_packages", IntDataValue),
        Field("num_main_packages", IntDataValue),
        Field("num_multiverse_packages", IntDataValue),
        Field("num_restricted_packages", IntDataValue),
        Field("num_universe_packages", IntDataValue),
        Field("num_third_party_packages", IntDataValue),
        Field("num_unknown_packages", IntDataValue),
        Field("num_esm_infra_packages", IntDataValue),
        Field("num_esm_apps_packages", IntDataValue),
        Field("num_standard_security_updates", IntDataValue),
        Field("num_esm_infra_updates", IntDataValue),
        Field("num_esm_apps_updates", IntDataValue),
    ]

    def __init__(
        self,
        ua: SecurityStatusSummaryUA,
        num_installed_packages: int,
        num_main_packages: int,
        num_multiverse_packages: int,
        num_restricted_packages: int,
        num_universe_packages: int,
        num_third_party_packages: int,
        num_unknown_packages: int,
        num_esm_infra_packages: int,
        num_esm_apps_packages: int,
        num_standard_security_updates: int,
        num_esm_infra_updates: int,
        num_esm_apps_updates: int,
    ):
        self.ua = ua
        self.num_installed_packages = num_installed_packages
        self.num_main_packages = num_main_packages
        self.num_multiverse_packages = num_multiverse_packages
        self.num_restricted_packages = num_restricted_packages
        self.num_universe_packages = num_universe_packages
        self.num_third_party_packages = num_third_party_packages
        self.num_unknown_packages = num_unknown_packages
        self.num_esm_infra_packages = num_esm_infra_packages
        self.num_esm_apps_packages = num_esm_apps_packages
        self.num_standard_security_updates = num_standard_security_updates
        self.num_esm_infra_updates = num_esm_infra_updates
        self.num_esm_apps_updates = num_esm_apps_updates


class SecurityStatusResult(DataObject):
    fields = [
        Field("_schema", StringDataValue),
        Field("summary", SecurityStatusSummary),
        Field("packages", data_list(SecurityStatusPackageUpdate)),
    ]

    def __init__(
        self,
        _schema: str,
        summary: SecurityStatusSummary,
        packages: List[SecurityStatusPackageUpdate],
    ):
        self._schema = _schema
        self.summary = summary
        self.packages = packages


def status(cfg=None) -> SecurityStatusResult:
    if cfg is None:
        cfg = UAConfig()

    ua_info = get_ua_info(cfg)

    installed_packages = get_installed_packages()

    package_count = defaultdict(int)  # type: DefaultDict[str, int]
    update_count = defaultdict(int)  # type: DefaultDict[str, int]

    for package in installed_packages:
        package_origin = get_origin_for_package(package)
        package_count[package_origin] += 1

    security_upgradable_versions = filter_security_updates(installed_packages)

    updates = []
    for candidate in security_upgradable_versions:
        service_name, origin_site = get_service_name(candidate.origins)
        status = get_update_status(service_name, ua_info)
        update_count[service_name] += 1
        updates.append(
            SecurityStatusPackageUpdate(
                package=candidate.package.name,
                version=candidate.version,
                service_name=service_name,
                status=status,
                origin=origin_site,
                download_size=candidate.size,
            )
        )

    return SecurityStatusResult(
        _schema="0.1",
        summary=SecurityStatusSummary(
            ua=SecurityStatusSummaryUA(
                attached=ua_info["attached"],
                enabled_services=ua_info["enabled_services"],
                entitled_services=ua_info["entitled_services"],
            ),
            num_installed_packages=len(installed_packages),
            num_main_packages=package_count["main"],
            num_multiverse_packages=package_count["multiverse"],
            num_restricted_packages=package_count["restricted"],
            num_universe_packages=package_count["universe"],
            num_third_party_packages=package_count["third-party"],
            num_unknown_packages=package_count["unknown"],
            num_esm_infra_packages=package_count["esm-infra"],
            num_esm_apps_packages=package_count["esm-apps"],
            num_standard_security_updates=update_count["standard-security"],
            num_esm_infra_updates=update_count["esm-infra"],
            num_esm_apps_updates=update_count["esm-apps"],
        ),
        packages=updates,
    )
