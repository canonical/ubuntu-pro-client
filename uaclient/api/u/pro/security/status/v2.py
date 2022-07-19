from typing import List

from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.api.u.pro.security.status import v1
from uaclient.data_types import DataObject, Field, IntDataValue, data_list

SecurityStatusPackageUpdate = v1.SecurityStatusPackageUpdate
SecurityStatusSummaryPro = v1.SecurityStatusSummaryUA


class SecurityStatusSummary(DataObject):
    fields = [
        Field("pro", SecurityStatusSummaryPro),
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
        pro: SecurityStatusSummaryPro,
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
        self.pro = pro
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


class SecurityStatusResult(DataObject, AdditionalInfo):
    fields = [
        Field("summary", SecurityStatusSummary),
        Field("updates", data_list(SecurityStatusPackageUpdate)),
    ]

    def __init__(
        self,
        summary: SecurityStatusSummary,
        updates: List[SecurityStatusPackageUpdate],
    ):
        self.summary = summary
        self.updates = updates


def status(cfg=None) -> SecurityStatusResult:
    v1_result = v1.status(cfg=cfg)
    return SecurityStatusResult(
        summary=SecurityStatusSummary(
            pro=v1_result.summary.ua,
            num_installed_packages=v1_result.summary.num_installed_packages,
            num_main_packages=v1_result.summary.num_main_packages,
            num_multiverse_packages=v1_result.summary.num_multiverse_packages,
            num_restricted_packages=v1_result.summary.num_restricted_packages,
            num_universe_packages=v1_result.summary.num_universe_packages,
            num_third_party_packages=(
                v1_result.summary.num_third_party_packages
            ),
            num_unknown_packages=v1_result.summary.num_unknown_packages,
            num_esm_infra_packages=v1_result.summary.num_esm_infra_packages,
            num_esm_apps_packages=v1_result.summary.num_esm_apps_packages,
            num_standard_security_updates=(
                v1_result.summary.num_standard_security_updates
            ),
            num_esm_infra_updates=v1_result.summary.num_esm_infra_updates,
            num_esm_apps_updates=v1_result.summary.num_esm_apps_updates,
        ),
        updates=v1_result.packages,
    )


endpoint = APIEndpoint(
    version="v2", name="SecurityStatus", fn=status, options_cls=None
)
