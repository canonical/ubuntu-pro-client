import datetime
from typing import Any, Dict, List, Optional

from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.api.u.pro.security.vulnerabilities._common.v1 import (
    SourcePackages,
    VulnerabilityData,
    VulnerabilityParser,
    VulnerabilityStatus,
    _get_vulnerability_fix_status,
)
from uaclient.apt import get_apt_cache_datetime
from uaclient.config import UAConfig
from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    DatetimeDataValue,
    Field,
    FloatDataValue,
    StringDataValue,
    data_list,
)


class CVEVulnerabilitiesOptions(DataObject):
    fields = [
        Field(
            "all",
            BoolDataValue,
            False,
            doc="Show all CVE vulnerabilities, even unfixable ones.",
        ),
        Field(
            "unfixable",
            BoolDataValue,
            False,
            doc="Show only unfixable CVES.",
        ),
        Field(
            "data_file",
            StringDataValue,
            False,
            doc="Path for a local vulnerabilities JSON data.",
        ),
        Field(
            "manifest_file",
            StringDataValue,
            False,
            doc="Path for manifest file to be used instead of locally installed packages.",  # noqa
        ),
        Field(
            "series",
            StringDataValue,
            False,
            doc=(
                "When provided, the API will download the JSON "
                "vulnerabilities data for the given series."
            ),
        ),
    ]

    def __init__(
        self,
        *,
        all: Optional[bool] = False,
        unfixable: Optional[bool] = False,
        data_file: Optional[str] = None,
        manifest_file: Optional[str] = None,
        series: Optional[str] = None
    ):
        self.all = all
        self.unfixable = unfixable
        self.data_file = data_file
        self.manifest_file = manifest_file
        self.series = series


class CVEAffectedPackage(DataObject):
    fields = [
        Field(
            "name",
            StringDataValue,
            doc="The name of the package",
        ),
        Field(
            "current_version",
            StringDataValue,
            doc="The current version of the package",
        ),
        Field(
            "fix_version",
            StringDataValue,
            False,
            doc="The version that fixes the CVE for the package",
        ),
        Field(
            "fix_status",
            StringDataValue,
            False,
            doc="The status of the CVE fix for the package",
        ),
        Field(
            "fix_available_from",
            StringDataValue,
            doc="The pocket where the fix is available from",
        ),
    ]

    def __init__(
        self,
        *,
        name: str,
        current_version: str,
        fix_status: str,
        fix_version: Optional[str] = None,
        fix_available_from: Optional[str] = None
    ):
        self.name = name
        self.current_version = current_version
        self.fix_version = fix_version
        self.fix_status = fix_status
        self.fix_available_from = fix_available_from


class CVEVulnerabilityResult(DataObject):
    fields = [
        Field(
            "name",
            StringDataValue,
            doc="The name of the CVE",
        ),
        Field(
            "description",
            StringDataValue,
            doc="The CVE description",
        ),
        Field(
            "published_at",
            DatetimeDataValue,
            doc="The CVE published date",
        ),
        Field(
            "ubuntu_priority",
            StringDataValue,
            doc="The ubuntu priority for the CVE",
        ),
        Field(
            "notes",
            data_list(StringDataValue),
            False,
            doc="A list of notes for the CVE",
        ),
        Field(
            "affected_packages",
            data_list(CVEAffectedPackage),
            doc="A list of affected packages for this CVE",
        ),
        Field(
            "fixable",
            StringDataValue,
            doc="The fixable status of the CVE",
        ),
        Field(
            "cvss_score",
            FloatDataValue,
            False,
            doc="The CVE cvss score",
        ),
        Field(
            "cvss_severity",
            StringDataValue,
            False,
            doc="The CVE cvss severity",
        ),
    ]

    def __init__(
        self,
        *,
        name: str,
        description: str,
        published_at: datetime.datetime,
        ubuntu_priority: str,
        fixable: str,
        notes: Optional[List[str]] = None,
        affected_packages: List[CVEAffectedPackage],
        cvss_score: Optional[float] = None,
        cvss_severity: Optional[str] = None
    ):
        self.name = name
        self.description = description
        self.published_at = published_at
        self.ubuntu_priority = ubuntu_priority
        self.fixable = fixable
        self.notes = notes
        self.affected_packages = affected_packages
        self.cvss_score = cvss_score
        self.cvss_severity = cvss_severity


class CVEVulnerabilitiesResult(DataObject, AdditionalInfo):
    fields = [
        Field(
            "cves",
            data_list(CVEVulnerabilityResult),
            doc="A list of CVEs that affect the system",
        ),
        Field(
            "vulnerability_data_published_at",
            DatetimeDataValue,
            doc="The date the JSON vulnerability data was published at",
        ),
        Field(
            "apt_updated_at",
            DatetimeDataValue,
            False,
            doc="The date of the last apt update operation in the system",
        ),
    ]

    def __init__(
        self,
        *,
        cves: List[CVEVulnerabilityResult],
        vulnerability_data_published_at: datetime.datetime,
        apt_updated_at: Optional[datetime.datetime] = None
    ):
        self.cves = cves
        self.vulnerability_data_published_at = vulnerability_data_published_at
        self.apt_updated_at = apt_updated_at


class CVEParser(VulnerabilityParser):
    vulnerability_type = "cves"

    def get_package_vulnerabilities(self, affected_pkg: Dict[str, Any]):
        return affected_pkg.get(self.vulnerability_type, {})


def vulnerabilities(
    options: CVEVulnerabilitiesOptions,
) -> CVEVulnerabilitiesResult:
    return _vulnerabilities(options, UAConfig())


def _vulnerabilities(
    options: CVEVulnerabilitiesOptions,
    cfg: UAConfig,
) -> CVEVulnerabilitiesResult:
    """
    This endpoint shows the CVE vulnerabilites in the system.
    By default, this API will only show fixable CVEs in the system.
    """

    vulnerabilities_json_data = VulnerabilityData(
        cfg=cfg, data_file=options.data_file, series=options.series
    ).get()

    installed_pkgs_by_source = SourcePackages(
        vulnerabilities_data=vulnerabilities_json_data,
        manifest_file=options.manifest_file,
    ).get()

    cve_parser = CVEParser()
    cve_parser.parse_data(
        vulnerabilities_data=vulnerabilities_json_data,
        installed_pkgs_by_source=installed_pkgs_by_source,
    )

    block_fixable_cves = False
    block_unfixable_cves = False

    if options.unfixable:
        block_fixable_cves = True

    if not options.unfixable and not options.all:
        block_unfixable_cves = True

    cves = []
    for cve_name, cve in cve_parser.vulnerabilities.items():
        cve_fix_status = _get_vulnerability_fix_status(
            cve["affected_packages"]
        )

        if (
            cve_fix_status != VulnerabilityStatus.NO_FIX_AVAILABLE
            and block_fixable_cves
        ):
            continue

        if (
            cve_fix_status == VulnerabilityStatus.NO_FIX_AVAILABLE
            and block_unfixable_cves
        ):
            continue

        cves.append(
            CVEVulnerabilityResult(
                name=cve_name,
                description=cve["description"],
                published_at=datetime.datetime.strptime(
                    cve["published_at"], "%Y-%m-%dT%H:%M:%S"
                ),
                ubuntu_priority=cve["ubuntu_priority"],
                notes=cve["notes"],
                affected_packages=[
                    CVEAffectedPackage(
                        name=pkg["name"],
                        current_version=pkg["current_version"],
                        fix_version=pkg["fix_version"],
                        fix_status=pkg["status"],
                        fix_available_from=pkg["fix_available_from"],
                    )
                    for pkg in cve["affected_packages"]
                ],
                fixable=cve_fix_status.value,
                cvss_score=cve["cvss_score"],
                cvss_severity=cve["cvss_severity"],
            )
        )

    return CVEVulnerabilitiesResult(
        cves=cves,
        vulnerability_data_published_at=datetime.datetime.strptime(
            vulnerabilities_json_data["published_at"], "%Y-%m-%dT%H:%M:%S"
        ),
        apt_updated_at=get_apt_cache_datetime(),
    )


endpoint = APIEndpoint(
    version="v1",
    name="CVEVulnerabilities",
    fn=_vulnerabilities,
    options_cls=CVEVulnerabilitiesOptions,
)

_doc = {
    "introduced_in": "34",
    "requires_network": True,
    "example_python": """
from uaclient.api.u.pro.security.vulnerabilities.cve.v1 import vulnerabilites, CVEVulnerabilitesOptions

options = CVEVulnerabilitiesOptions()
result = vulnerabilities(options)
""",  # noqa: E501
    "result_class": CVEVulnerabilitiesResult,
    "ignore_result_classes": [DataObject],
    "extra_result_classes": [
        CVEAffectedPackage,
        CVEVulnerabilityResult,
    ],
    "exceptions": [],
    "example_cli": "pro api u.pro.security.vulnerabilities.cve.v1",
    "example_json": """
{
    "apt_updated_at": "2024-07-26T20:53:55.708438+00:00",
    "cves": [
      {
        "affected_packages": [
          {
            "current_version": "1.3.1+dfsg-1~ubuntu0.16.04.1",
            "fix_available_from": "esm-infra",
            "fix_status": "fixed",
            "fix_version": ".*",
            "name": "libzstd1"
          }
        ],
        "cvss_score": 8.1,
        "cvss_severity": "high",
        "description": "CVE description",
        "fixable": "yes",
        "name": "CVE-2019-11922",
        "notes": [],
        "published_at": "2024-07-23T20:53:55.708438+00:00",
        "ubuntu_priority": "medium"
      }
    ],
    "vulnerability_data_published_at": "2024-07-26T20:53:55.708438+00:00"
}
""",
}
