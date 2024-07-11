import datetime
import json
from typing import List, Optional

from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.api.u.pro.packages.updates.v1 import (
    PackageUpdatesResult,
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
    IntDataValue,
    StringDataValue,
    data_list,
)


class UpdateInfoWithCVESOptions(DataObject):
    fields = [
        Field("data_file", StringDataValue, False),
        Field("series", StringDataValue, False),
        Field("updates_data", StringDataValue, False),
    ]

    def __init__(
        self,
        *,
        data_file: Optional[str] = None,
        series: Optional[str] = None,
        updates_data: Optional[str] = None
    ):
        self.data_file = data_file
        self.series = series
        self.updates_data = updates_data


class UpdateInfoWithCVES(DataObject):
    fields = [
        Field("download_size", IntDataValue),
        Field("origin", StringDataValue),
        Field("package", StringDataValue),
        Field("provided_by", StringDataValue),
        Field("status", StringDataValue),
        Field("version", StringDataValue),
        Field("related_cves", data_list(StringDataValue)),
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
        self.download_size = download_size
        self.origin = origin
        self.package = package
        self.provided_by = provided_by
        self.status = status
        self.version = version
        self.related_cves = related_cves


class CVEInfo(DataObject):
    fields = [
        Field("name", StringDataValue),
        Field("description", StringDataValue),
        Field("published_at", DatetimeDataValue),
        Field("ubuntu_priority", StringDataValue),
        Field("notes", data_list(StringDataValue)),
        Field("cvss_score", FloatDataValue),
        Field("cvss_severity", StringDataValue),
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


class PackageUpdatesWithCVEResult(DataObject, AdditionalInfo):
    fields = [
        Field("summary", UpdateSummary),
        Field("updates", data_list(UpdateInfoWithCVES)),
        Field("cves", data_list(CVEInfo)),
        Field("vulnerability_data_published_at", DatetimeDataValue),
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
    options: UpdateInfoWithCVESOptions,
) -> PackageUpdatesWithCVEResult:
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
    options: UpdateInfoWithCVESOptions, cfg: UAConfig
) -> PackageUpdatesWithCVEResult:

    package_updates = _get_pkg_updates(cfg, options.updates_data)
    vulnerabilities_json_data = VulnerabilityData(
        cfg=cfg, data_file=options.data_file, series=options.series
    ).get()
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
                cve_fixed_version = cve_info["source_fixed_version"]
                if not cve_fixed_version:
                    continue

                if version_compare(current_pkg_version, cve_fixed_version) < 0:
                    if version_compare(update_version, cve_fixed_version) >= 0:
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
                    related_cves=related_cves,
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

    return PackageUpdatesWithCVEResult(
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
    options_cls=UpdateInfoWithCVESOptions,
)
