import datetime
from typing import Any, Dict, List, Optional

from uaclient import system, util
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.api.u.pro.security.cves._common.v1 import (
    VulnerabilityParser,
    get_vulnerabilities,
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
    data_dict,
    data_list,
)


class CVEsOptions(DataObject):
    fields = [
        Field(
            "unfixable",
            BoolDataValue,
            False,
            doc="Show only unfixable CVES.",
        ),
        Field(
            "fixable",
            BoolDataValue,
            False,
            doc="Show only fixable CVES.",
        ),
    ]

    def __init__(
        self,
        *,
        unfixable: Optional[bool] = False,
        fixable: Optional[bool] = False
    ):
        self.unfixable = unfixable
        self.fixable = fixable


class CVEAffectedPackage(DataObject):
    fields = [
        Field(
            "name",
            StringDataValue,
            False,
            doc="The CVE name",
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
            "fix_origin",
            StringDataValue,
            doc="The pocket where the fix is available from",
        ),
    ]

    def __init__(
        self, name: str, fix_version: str, fix_status: str, fix_origin: str
    ):
        self.name = name
        self.fix_version = fix_version
        self.fix_status = fix_status
        self.fix_origin = fix_origin


class AffectedPackage(DataObject):
    fields = [
        Field(
            "current_version",
            StringDataValue,
            doc="The current version of the package",
        ),
        Field(
            "cves",
            data_list(CVEAffectedPackage),
            doc="The CVE that affects the package",
        ),
    ]

    def __init__(
        self, *, current_version: str, cves: List[CVEAffectedPackage]
    ):
        self.current_version = current_version
        self.cves = cves


class RelatedUSN(DataObject):
    fields = [
        Field(
            "name",
            StringDataValue,
            doc="The USN name",
        ),
        Field(
            "title",
            StringDataValue,
            doc="The USN title",
        ),
    ]

    def __init__(self, name: str, title: str):
        self.name = name
        self.title = title


class CVEInfo(DataObject):
    fields = [
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
            "priority",
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
        *,
        description: str,
        published_at: datetime.datetime,
        priority: str,
        notes: Optional[List[str]] = None,
        cvss_score: Optional[float] = None,
        cvss_severity: Optional[str] = None,
        related_usns: Optional[List[RelatedUSN]] = None,
        related_packages: Optional[List[str]] = None
    ):
        self.description = description
        self.published_at = published_at
        self.priority = priority
        self.notes = notes
        self.cvss_score = cvss_score
        self.cvss_severity = cvss_severity
        # These fields do not appear on the Fields list
        # because we want to access them in the CLI, but
        # not output them in the API
        self.related_usns = related_usns
        self.related_packages = related_packages


class CVEsResult(DataObject, AdditionalInfo):
    fields = [
        Field(
            "packages",
            data_dict(value_cls=AffectedPackage),
            doc="A dictionary where the keys are installed package names and the values are AffectedPackage objects.",  # noqa
        ),
        Field(
            "cves",
            data_dict(value_cls=CVEInfo),
            doc="A dictionary where the keys are CVE names and the values are CVEInfo objects.",  # noqa
        ),
    ]

    def __init__(
        self,
        *,
        packages: Dict[str, AffectedPackage],
        cves: Dict[str, CVEInfo],
        # These fields do not appear on the Fields list
        # because we want to access them in the CLI, but
        # not output them in the API
        vulnerability_data_published_at: datetime.datetime,
        apt_updated_at: Optional[datetime.datetime] = None
    ):
        self.packages = packages
        self.cves = cves
        self.vulnerability_data_published_at = vulnerability_data_published_at
        self.apt_updated_at = apt_updated_at


class CVEParser(VulnerabilityParser):
    vulnerability_type = "cves"

    def get_package_vulnerabilities(
        self, affected_pkg: Dict[str, Any]
    ) -> Dict[str, Any]:
        return affected_pkg.get(self.vulnerability_type, {})

    def _post_process_vulnerability_info(
        self,
        vulnerability_info: Dict[str, Any],
        vulnerabilities_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        if vulnerability_info.get("related_usns"):
            related_usns = []

            usn_info = vulnerabilities_data.get("security_issues", {}).get(
                "usns", {}
            )

            for related_usn in vulnerability_info["related_usns"]:
                related_usns.append(
                    {
                        "name": related_usn,
                        "title": usn_info.get(related_usn, {}).get(
                            "title", ""
                        ),
                    }
                )

            vulnerability_info["related_usns"] = related_usns

        return vulnerability_info


def cve_status_match_options(cve, options) -> bool:
    is_fixable = cve.get("fix_version") and cve.get("fix_origin")

    if options.unfixable and is_fixable:
        return False
    elif options.fixable and not is_fixable:
        return False
    return True


def cves(
    options: CVEsOptions,
) -> CVEsResult:
    return _cves(options, UAConfig())


def _parse_vulnerabilities(
    options: CVEsOptions,
    vulnerabilities: Dict[str, Any],
    vulnerability_data_published_at: str,
) -> CVEsResult:
    packages = {}
    allowed_cves = set()
    for pkg_name, package_info in sorted(
        vulnerabilities.get("packages", {}).items()
    ):
        pkg_cves = []
        for cve in sorted(
            package_info.get("cves", []), key=lambda cve: cve["name"]
        ):
            if cve_status_match_options(cve, options):
                pkg_cves.append(
                    CVEAffectedPackage(
                        name=cve["name"],
                        fix_version=cve["fix_version"],
                        fix_status=cve["fix_status"],
                        fix_origin=cve["fix_origin"],
                    )
                )
                allowed_cves.add(cve["name"])

        if pkg_cves:
            packages[pkg_name] = AffectedPackage(
                current_version=package_info["current_version"],
                cves=pkg_cves,
            )

    cves = {
        cve_name: CVEInfo(
            description=cve["description"],
            published_at=util.parse_rfc3339_date(cve["published_at"]),
            priority=cve["ubuntu_priority"],
            notes=cve["notes"],
            cvss_score=cve["cvss_score"],
            cvss_severity=cve["cvss_severity"],
            related_usns=[
                RelatedUSN(
                    name=related_usn.get("name", ""),
                    title=related_usn.get("title", ""),
                )
                for related_usn in cve.get("related_usns", [])
            ],
            related_packages=cve.get("related_packages", []),
        )
        for cve_name, cve in sorted(
            vulnerabilities.get("vulnerabilities", {}).items(),
            key=lambda v: v[0],
        )
        if cve_name in allowed_cves
    }

    return CVEsResult(
        packages=packages,
        cves=cves,
        vulnerability_data_published_at=util.parse_rfc3339_date(
            vulnerability_data_published_at
        ),
        apt_updated_at=get_apt_cache_datetime(),
    )


def _cves(
    options: CVEsOptions,
    cfg: UAConfig,
) -> CVEsResult:
    """
    This endpoint shows the CVE vulnerabilites in the system.
    By default, this API will show all CVEs that affect the system.
    """

    # By default we return all affected CVEs. If a user provides
    # both options, we just switch to the default approach
    if options.unfixable and options.fixable:
        options.unfixable = False
        options.fixable = False

    series = system.get_release_info().series

    cve_vulnerabilities_result = get_vulnerabilities(
        parser=CVEParser(),
        cfg=cfg,
        series=series,
    )
    cve_vulnerabilities = cve_vulnerabilities_result.vulnerabilities_info

    return _parse_vulnerabilities(
        options=options,
        vulnerabilities=cve_vulnerabilities,
        vulnerability_data_published_at=cve_vulnerabilities_result.vulnerability_data_published_at,  # noqa
    )


endpoint = APIEndpoint(
    version="v1",
    name="CVEs",
    fn=_cves,
    options_cls=CVEsOptions,
)

_doc = {
    "introduced_in": "35",
    "requires_network": True,
    "example_python": """
from uaclient.api.u.pro.security.cves.v1 import cves, CVEsOptions

options = CVEsOptions()
result = cves(options)
""",  # noqa: E501
    "result_class": CVEsResult,
    "ignore_result_classes": [DataObject],
    "exceptions": [],
    "example_cli": "pro api u.pro.security.cves.v1",
    "example_json": """
{
    "cves": {
      "CVE-2023-5678": {
        "cvss_score": 8.1,
        "cvss_severity": "high",
        "description": "description example",
        "notes": [
          "note example",
        ],
        "priority": "medium",
        "published_at": ".*"
      }
    },
    "packages": {
      "accountsservice": {
        "current_version": "0.6.40-2ubuntu11.6",
        "cves": [
          {
            "fix_origin": "esm-infra",
            "fix_status": "fixed",
            "fix_version": "0.6.40-2ubuntu11.6+esm1",
            "name": "CVE-2023-5678"
          }
        ]
      },
      "libaccountsservice0": {
        "current_version": "0.6.40-2ubuntu11.6",
        "cves": [
          {
            "fix_origin": "esm-infra",
            "fix_status": "fixed",
            "fix_version": "0.6.40-2ubuntu11.6+esm1",
            "name": "CVE-2023-5678"
          }
        ]
      }
    },
}
""",
}
