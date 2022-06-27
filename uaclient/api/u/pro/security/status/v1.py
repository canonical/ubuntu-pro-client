from typing import List

from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    Field,
    IntDataValue,
    StringDataValue,
    data_list,
)


class SecurityStatusPackageUpdate(DataObject):
    fields = [
        Field("package", StringDataValue),
        Field("version", StringDataValue),
        Field("service_name", StringDataValue),
        Field("origin", StringDataValue),
        Field("status", StringDataValue),
    ]

    def __init__(
        self,
        package: str,
        version: str,
        service_name: str,
        origin: str,
        status: str,
    ):
        self.package = package
        self.version = version
        self.service_name = service_name
        self.origin = origin
        self.status = status


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


def status() -> SecurityStatusResult:
    pass
