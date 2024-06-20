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
    StringDataValue,
    data_list,
)
from uaclient.system import get_release_info


class USNVulnerabilitiesOptions(DataObject):
    fields = [
        Field("all", BoolDataValue, False),
        Field("unfixable", BoolDataValue, False),
    ]

    def __init__(
        self, *, all: Optional[bool] = False, unfixable: Optional[bool] = False
    ):
        self.all = all
        self.unfixable = unfixable


class USNAffectedPackage(DataObject):
    fields = [
        Field("name", StringDataValue),
        Field("current_version", StringDataValue),
        Field("fix_version", StringDataValue, False),
        Field("fix_available_from", StringDataValue),
    ]

    def __init__(
        self,
        *,
        name: str,
        current_version: str,
        fix_version: Optional[str] = None,
        fix_available_from: Optional[str] = None
    ):
        self.name = name
        self.current_version = current_version
        self.fix_version = fix_version
        self.fix_available_from = fix_available_from


class USNVulnerabilityResult(DataObject):
    fields = [
        Field("name", StringDataValue),
        Field("description", StringDataValue),
        Field("published_at", DatetimeDataValue),
        Field("affected_packages", data_list(USNAffectedPackage)),
        Field("fixable", BoolDataValue),
        Field("related_cves", data_list(StringDataValue)),
        Field("related_launchpad_bugs", data_list(StringDataValue)),
    ]

    def __init__(
        self,
        *,
        name: str,
        description: str,
        published_at: datetime.datetime,
        fixable: bool,
        affected_packages: List[USNAffectedPackage],
        related_cves: List[str],
        related_launchpad_bugs: List[str],
    ):
        self.name = name
        self.description = description
        self.published_at = published_at
        self.fixable = fixable
        self.affected_packages = affected_packages
        self.related_cves = related_cves
        self.related_launchpad_bugs = related_launchpad_bugs


class USNVulnerabilitiesResult(DataObject, AdditionalInfo):
    fields = [
        Field("usns", data_list(USNVulnerabilityResult)),
        Field("vulnerability_data_published_at", DatetimeDataValue),
        Field("apt_updated_at", DatetimeDataValue, False),
    ]

    def __init__(
        self,
        *,
        usns: List[USNVulnerabilityResult],
        vulnerability_data_published_at: datetime.datetime,
        apt_updated_at: Optional[datetime.datetime] = None
    ):
        self.usns = usns
        self.vulnerability_data_published_at = vulnerability_data_published_at
        self.apt_updated_at = apt_updated_at


class USNParser(VulnerabilityParser):
    vulnerability_type = "usns"

    def get_package_vulnerabilities(self, affected_pkg: Dict[str, Any]):
        return {
            **affected_pkg.get("ubuntu_security_notices", {}),
            **affected_pkg.get("ubuntu_security_notices_regressions", {}),
        }


def vulnerabilities(
    options: USNVulnerabilitiesOptions,
) -> USNVulnerabilitiesResult:
    return _vulnerabilities(options, UAConfig())


def _vulnerabilities(
    options: USNVulnerabilitiesOptions,
    cfg: UAConfig,
) -> USNVulnerabilitiesResult:
    series = get_release_info().series

    vulnerabilities_json_data = fetch_vulnerabilities_data(cfg, series)
    installed_pkgs_by_source = query_installed_source_pkg_versions()

    usn_parser = USNParser()
    usn_parser.parse_data(
        vulnerabilities_data=vulnerabilities_json_data,
        installed_pkgs_by_source=installed_pkgs_by_source,
    )

    block_fixable_usns = False
    block_unfixable_usns = False

    if options.unfixable:
        block_fixable_usns = True

    if not options.unfixable and not options.all:
        block_unfixable_usns = True

    usns = []
    for usn_name, usn in sorted(usn_parser.vulnerabilities.items()):
        if usn["fixable"] and block_fixable_usns:
            continue

        if not usn["fixable"] and block_unfixable_usns:
            continue

        usns.append(
            USNVulnerabilityResult(
                name=usn_name,
                description=usn["description"],
                published_at=datetime.datetime.strptime(
                    usn["published_at"], "%Y-%m-%dT%H:%M:%S"
                ),
                fixable=usn["fixable"],
                affected_packages=[
                    USNAffectedPackage(
                        name=pkg["name"],
                        current_version=pkg["current_version"],
                        fix_version=pkg["fix_version"],
                        fix_available_from=pkg["fix_available_from"],
                    )
                    for pkg in usn["affected_packages"]
                ],
                related_cves=usn["related_cves"],
                related_launchpad_bugs=usn["related_launchpad_bugs"],
            )
        )

    return USNVulnerabilitiesResult(
        usns=usns,
        vulnerability_data_published_at=datetime.datetime.strptime(
            vulnerabilities_json_data["published_at"], "%Y-%m-%dT%H:%M:%S"
        ),
        apt_updated_at=get_apt_cache_datetime(),
    )


endpoint = APIEndpoint(
    version="v1",
    name="USNVulnerabilities",
    fn=_vulnerabilities,
    options_cls=USNVulnerabilitiesOptions,
)
