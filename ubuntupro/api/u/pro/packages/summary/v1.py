from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, IntDataValue
from uaclient.security_status import get_installed_packages_by_origin


class PackageSummary(DataObject):
    fields = [
        Field("num_installed_packages", IntDataValue),
        Field("num_esm_apps_packages", IntDataValue),
        Field("num_esm_infra_packages", IntDataValue),
        Field("num_main_packages", IntDataValue),
        Field("num_multiverse_packages", IntDataValue),
        Field("num_restricted_packages", IntDataValue),
        Field("num_third_party_packages", IntDataValue),
        Field("num_universe_packages", IntDataValue),
        Field("num_unknown_packages", IntDataValue),
    ]

    def __init__(
        self,
        num_installed_packages: int,
        num_esm_apps_packages: int,
        num_esm_infra_packages: int,
        num_main_packages: int,
        num_multiverse_packages: int,
        num_restricted_packages: int,
        num_third_party_packages: int,
        num_universe_packages: int,
        num_unknown_packages: int,
    ):
        self.num_installed_packages = num_installed_packages
        self.num_esm_apps_packages = num_esm_apps_packages
        self.num_esm_infra_packages = num_esm_infra_packages
        self.num_main_packages = num_main_packages
        self.num_multiverse_packages = num_multiverse_packages
        self.num_restricted_packages = num_restricted_packages
        self.num_third_party_packages = num_third_party_packages
        self.num_universe_packages = num_universe_packages
        self.num_unknown_packages = num_unknown_packages


class PackageSummaryResult(DataObject, AdditionalInfo):
    fields = [Field("summary", PackageSummary)]

    def __init__(self, summary):
        self.summary = summary


def summary() -> PackageSummaryResult:
    return _summary(UAConfig())


def _summary(cfg: UAConfig) -> PackageSummaryResult:
    packages = get_installed_packages_by_origin()
    summary = PackageSummary(
        num_installed_packages=len(packages["all"]),
        num_esm_apps_packages=len(packages["esm-apps"]),
        num_esm_infra_packages=len(packages["esm-infra"]),
        num_main_packages=len(packages["main"]),
        num_multiverse_packages=len(packages["multiverse"]),
        num_restricted_packages=len(packages["restricted"]),
        num_third_party_packages=len(packages["third-party"]),
        num_universe_packages=len(packages["universe"]),
        num_unknown_packages=len(packages["unknown"]),
    )
    return PackageSummaryResult(summary=summary)


endpoint = APIEndpoint(
    version="v1",
    name="PackageSummary",
    fn=_summary,
    options_cls=None,
)
