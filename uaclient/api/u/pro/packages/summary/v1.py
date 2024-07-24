from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, IntDataValue
from uaclient.security_status import get_installed_packages_by_origin


class PackageSummary(DataObject):
    fields = [
        Field(
            "num_installed_packages",
            IntDataValue,
            doc="Total count of installed packages",
        ),
        Field(
            "num_esm_apps_packages",
            IntDataValue,
            doc="Count of packages installed from ``esm-apps``",
        ),
        Field(
            "num_esm_infra_packages",
            IntDataValue,
            doc="Count of packages installed from ``esm-infra``",
        ),
        Field(
            "num_main_packages",
            IntDataValue,
            doc="Count of packages installed from ``main``",
        ),
        Field(
            "num_multiverse_packages",
            IntDataValue,
            doc="Count of packages installed from ``multiverse``",
        ),
        Field(
            "num_restricted_packages",
            IntDataValue,
            doc="Count of packages installed from ``restricted``",
        ),
        Field(
            "num_third_party_packages",
            IntDataValue,
            doc="Count of packages installed from third party sources",
        ),
        Field(
            "num_universe_packages",
            IntDataValue,
            doc="Count of packages installed from ``universe``",
        ),
        Field(
            "num_unknown_packages",
            IntDataValue,
            doc="Count of packages installed from unknown sources",
        ),
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
    fields = [
        Field(
            "summary",
            PackageSummary,
            doc=("Summary of all installed packages"),
        )
    ]

    def __init__(self, summary):
        self.summary = summary


def summary() -> PackageSummaryResult:
    return _summary(UAConfig())


def _summary(cfg: UAConfig) -> PackageSummaryResult:
    """
    This endpoint shows a summary of installed packages in the system,
    categorised by origin.
    """
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

_doc = {
    "introduced_in": "27.12",
    "requires_network": False,
    "example_python": """
from uaclient.api.u.pro.packages.summary.v1 import summary

result = summary()
""",  # noqa: E501
    "result_class": PackageSummaryResult,
    "exceptions": [],
    "example_cli": "pro api u.pro.packages.summary.v1",
    "example_json": """
{
    "summary":{
        "num_installed_packages": 1,
        "num_esm_apps_packages": 2,
        "num_esm_infra_packages": 3,
        "num_main_packages": 4,
        "num_multiverse_packages": 5,
        "num_restricted_packages": 6,
        "num_third_party_packages": 7,
        "num_universe_packages": 8,
        "num_unknown_packages": 9,
    },
}
""",
}
