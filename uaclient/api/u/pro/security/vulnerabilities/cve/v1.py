import datetime
from typing import Any, Dict, List, Optional

from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.api.u.pro.security.fix._common import (
    query_installed_source_pkg_versions,
)
from uaclient.api.u.pro.security.vulnerabilities._common.v1 import (
    VulnerabilityParser,
    VulnerabilityStatus,
    _get_vulnerability_fix_status,
    fetch_vulnerabilities_data,
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
from uaclient.system import get_release_info


class CVEVulnerabilitiesOptions(DataObject):
    fields = [
        Field("all", BoolDataValue, False),
        Field("unfixable", BoolDataValue, False),
    ]

    def __init__(
        self, *, all: Optional[bool] = False, unfixable: Optional[bool] = False
    ):
        self.all = all
        self.unfixable = unfixable


class CVEAffectedPackage(DataObject):
    fields = [
        Field("name", StringDataValue),
        Field("current_version", StringDataValue),
        Field("fix_version", StringDataValue, False),
        Field("fix_status", StringDataValue, False),
        Field("fix_available_from", StringDataValue),
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
        Field("name", StringDataValue),
        Field("description", StringDataValue),
        Field("published_at", DatetimeDataValue),
        Field("ubuntu_priority", StringDataValue),
        Field("notes", data_list(StringDataValue), False),
        Field("affected_packages", data_list(CVEAffectedPackage)),
        Field("fixable", StringDataValue),
        Field("cvss_score", FloatDataValue, False),
        Field("cvss_severity", StringDataValue, False),
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
        Field("cves", data_list(CVEVulnerabilityResult)),
        Field("vulnerability_data_published_at", DatetimeDataValue),
        Field("apt_updated_at", DatetimeDataValue, False),
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
    series = get_release_info().series

    vulnerabilities_json_data = fetch_vulnerabilities_data(cfg, series)
    installed_pkgs_by_source = query_installed_source_pkg_versions()

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
