import datetime
import json
from typing import List, Optional

from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.api.u.pro.packages.updates.v1 import (
    PackageUpdatesResult,
    UpdateInfo,
    UpdateSummary,
    _updates,
)
from uaclient.api.u.pro.security.vulnerabilities._common.v1 import (
    VulnerabilityData,
    _get_source_package_from_vulnerabilities_data,
)
from uaclient.apt import PreserveAptCfg, get_apt_pkg_cache, version_compare
from uaclient.config import UAConfig
from uaclient.data_types import (
    DataObject,
    DatetimeDataValue,
    Field,
    FloatDataValue,
    StringDataValue,
    data_list,
)


class UpdatesInfoWithCVEsOptions(DataObject):
    fields = [
        Field(
            "updates_data",
            StringDataValue,
            False,
            doc=(
                "The updates data collected from u.pro.packages.updates.v1."
                "When used, the API will not collect local available updates,"
                " but instead rely on the updates data for this information"
            ),
        ),
    ]

    def __init__(self, *, updates_data: Optional[str] = None):
        self.updates_data = updates_data


class UpdateInfoWithCVES(UpdateInfo):
    fields = UpdateInfo.fields + [
        Field(
            "related_cves",
            data_list(StringDataValue),
            doc="A list of CVEs that are tied to this package update",
        )
    ]

    def __init__(
        self,
        download_size: int,
        origin: str,
        package: str,
        provided_by: str,
        status: str,
        version: str,
        related_cves: List[str],
    ):
        super().__init__(
            download_size=download_size,
            origin=origin,
            package=package,
            provided_by=provided_by,
            status=status,
            version=version,
        )
        self.related_cves = related_cves


class CVEInfo(DataObject):
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
        name: str,
        description: str,
        published_at: datetime.datetime,
        ubuntu_priority: str,
        notes: List[str],
        cvss_score: float,
        cvss_severity: str,
    ):
        self.name = name
        self.description = description
        self.published_at = published_at
        self.ubuntu_priority = ubuntu_priority
        self.notes = notes
        self.cvss_score = cvss_score
        self.cvss_severity = cvss_severity


class PackageUpdatesWithCVEsResult(DataObject, AdditionalInfo):
    fields = [
        Field(
            "summary", UpdateSummary, doc="Summary of all available updates"
        ),
        Field(
            "updates",
            data_list(UpdateInfoWithCVES),
            doc="Detailed list of all available updates",
        ),
        Field(
            "cves",
            data_list(CVEInfo),
            doc="A list of CVEs that affect the system",
        ),
        Field(
            "vulnerability_data_published_at",
            DatetimeDataValue,
            doc="The date the JSON vulnerability data was published at",
        ),
    ]

    def __init__(
        self,
        summary: UpdateSummary,
        updates: List[UpdateInfoWithCVES],
        cves: List[CVEInfo],
        vulnerability_data_published_at: datetime.datetime,
    ):
        self.summary = summary
        self.updates = updates
        self.cves = cves
        self.vulnerability_data_published_at = vulnerability_data_published_at


def updates_with_cves(
    options: UpdatesInfoWithCVEsOptions,
) -> PackageUpdatesWithCVEsResult:
    return _updates_with_cves(options=options, cfg=UAConfig())


def _get_pkg_current_version(cache, pkg: str):
    return cache[pkg].current_ver.ver_str


def _get_pkg_updates(cfg: UAConfig, updates_data: Optional[str]):
    if not updates_data:
        return _updates(cfg)

    with open(updates_data, "r") as f:
        package_updates = json.loads(f.read())
        return PackageUpdatesResult.from_dict(
            package_updates["data"]["attributes"]
        )


def _updates_with_cves(
    options: UpdatesInfoWithCVEsOptions, cfg: UAConfig
) -> PackageUpdatesWithCVEsResult:
    """
    This endpoint shows available updates for packages in a system including
    the CVEs that are tied to each update.
    """

    package_updates = _get_pkg_updates(cfg, options.updates_data)
    vulnerabilities_json_data = VulnerabilityData(cfg=cfg).get()
    package_updates_with_cves = []
    cves_info = []
    all_cves = set()

    with PreserveAptCfg(get_apt_pkg_cache) as cache:
        for pkg in package_updates.updates:
            related_cves = []

            pkg_name = pkg.package

            source_pkg = _get_source_package_from_vulnerabilities_data(
                vulnerabilities_json_data, pkg_name
            )
            update_version = pkg.version
            current_pkg_version = _get_pkg_current_version(cache, pkg_name)

            pkg_cves = (
                vulnerabilities_json_data.get("packages")
                .get(source_pkg, {})
                .get("cves", {})
            )

            for cve_name, cve_info in pkg_cves.items():
                cve_source_fixed_version = cve_info["source_fixed_version"]
                if not cve_source_fixed_version:
                    continue

                cve_binary_fixed_version = (
                    vulnerabilities_json_data.get("packages")
                    .get(source_pkg, {})
                    .get("source_versions", {})
                    .get(cve_source_fixed_version, {})
                    .get("binary_packages", {})
                    .get(pkg_name)
                )

                if not cve_binary_fixed_version:
                    continue

                if (
                    version_compare(
                        current_pkg_version, cve_binary_fixed_version
                    )
                    < 0
                ):
                    if (
                        version_compare(
                            update_version, cve_binary_fixed_version
                        )
                        >= 0
                    ):
                        related_cves.append(cve_name)
                        all_cves.add(cve_name)

            package_updates_with_cves.append(
                UpdateInfoWithCVES(
                    download_size=pkg.download_size,
                    origin=pkg.origin,
                    package=pkg_name,
                    provided_by=pkg.provided_by,
                    status=pkg.status,
                    version=update_version,
                    related_cves=sorted(related_cves),
                )
            )

    cves = vulnerabilities_json_data.get("security_issues", {}).get("cves", {})
    for cve_name in sorted(all_cves):
        cve = cves.get(cve_name)
        cves_info.append(
            CVEInfo(
                name=cve_name,
                description=cve["description"],
                published_at=datetime.datetime.strptime(
                    cve["published_at"], "%Y-%m-%dT%H:%M:%S"
                ),
                ubuntu_priority=cve["ubuntu_priority"],
                notes=cve["notes"],
                cvss_score=cve["cvss_score"],
                cvss_severity=cve["cvss_severity"],
            )
        )

    return PackageUpdatesWithCVEsResult(
        summary=package_updates.summary,
        updates=package_updates_with_cves,
        cves=cves_info,
        vulnerability_data_published_at=datetime.datetime.strptime(
            vulnerabilities_json_data["published_at"], "%Y-%m-%dT%H:%M:%S"
        ),
    )


endpoint = APIEndpoint(
    version="v1",
    name="PackageUpdatesWithCVE",
    fn=_updates_with_cves,
    options_cls=UpdatesInfoWithCVEsOptions,
)

_doc = {
    "introduced_in": "35",
    "requires_network": True,
    "example_python": """
from uaclient.api.u.pro.packages.updates_with_cves.v1 import updates, UpdatesInfoWithCVEsOptions

options = UpdatesInfoWithCVEsOptions()
result = updates(options)
""",  # noqa: E501
    "result_class": PackageUpdatesWithCVEsResult,
    "exceptions": [],
    "example_cli": "pro api u.pro.packages.updates_with_cves.v1",
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
            related_cves=["CVE-5678-123"],
        },
    ],
    "cves": [
      {
        "name": "CVE-5678-123",
        "cvss_score": 8.1,
        "cvss_severity": "high",
        "description": "CVE description",
        "notes": [],
        "published_at": "2024-07-23T20:53:55.708438+00:00",
        "ubuntu_priority": "medium"
      }
    ],
    "vulnerability_data_published_at": "2024-07-26T20:53:55.708438+00:00"
}
""",
}
