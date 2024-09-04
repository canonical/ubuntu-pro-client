import datetime
from typing import Any, Dict, List, Optional

from uaclient import util
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.api.exceptions import InvalidOptionCombination
from uaclient.api.u.pro.security.vulnerabilities._common.v1 import (
    VulnerabilityParser,
    VulnerabilityStatus,
    _get_vulnerability_fix_status,
    get_vulnerabilities,
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


class USNVulnerabilitiesOptions(DataObject):
    fields = [
        Field(
            "all",
            BoolDataValue,
            False,
            doc="Show all USN vulnerabilities, even unfixable ones.",
        ),
        Field(
            "unfixable",
            BoolDataValue,
            False,
            doc="Show only unfixable USNs.",
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
        Field(
            "update",
            BoolDataValue,
            False,
            doc=(
                "If the vulnerability data should automatically "
                "be updated when running the command (default=True)"
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
        series: Optional[str] = None,
        update: Optional[bool] = None
    ):
        self.all = all
        self.unfixable = unfixable
        self.data_file = data_file
        self.manifest_file = manifest_file
        self.series = series

        if update is None:
            update = True

        self.update = update


class USNAffectedPackage(DataObject):
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
        fix_version: Optional[str] = None,
        fix_available_from: Optional[str] = None
    ):
        self.name = name
        self.current_version = current_version
        self.fix_version = fix_version
        self.fix_available_from = fix_available_from


class USNVulnerabilityResult(DataObject):
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
            "affected_packages",
            data_list(USNAffectedPackage),
            doc="A list of affected packages for this USN",
        ),
        Field(
            "fixable",
            StringDataValue,
            doc="The fixable status of the CVE",
        ),
        Field(
            "related_cves",
            data_list(StringDataValue),
            doc="A list of CVEs related to this USN",
        ),
        Field(
            "related_launchpad_bugs",
            data_list(StringDataValue),
            doc="A list of Launchpad bugs related to this USN",
        ),
    ]

    def __init__(
        self,
        *,
        name: str,
        description: str,
        published_at: datetime.datetime,
        affected_packages: List[USNAffectedPackage],
        fixable: str,
        related_cves: List[str],
        related_launchpad_bugs: List[str]
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
        Field(
            "usns",
            data_list(USNVulnerabilityResult),
            doc="A list of USNs that affect the system",
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

    def _post_process_vulnerability_info(
        self,
        installed_pkgs_by_source: Dict[str, Dict[str, str]],
        vulnerability_info: Dict[str, Any],
        vulnerabilities_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        return vulnerability_info


def vulnerabilities(
    options: USNVulnerabilitiesOptions,
) -> USNVulnerabilitiesResult:
    return _vulnerabilities(options, UAConfig())


def _vulnerabilities(
    options: USNVulnerabilitiesOptions,
    cfg: UAConfig,
) -> USNVulnerabilitiesResult:
    """
    This endpoint shows the USN vulnerabilites in the system.
    By default, this API will only show fixable USNs in the system.
    """

    if options.unfixable and options.all:
        raise InvalidOptionCombination(option1="unfixable", option2="all")

    usn_vulnerabilities_result = get_vulnerabilities(
        parser=USNParser(),
        cfg=cfg,
        update_json_data=options.update,
        series=options.series,
        data_file=options.data_file,
        manifest_file=options.manifest_file,
    )
    usn_vulnerabilities = usn_vulnerabilities_result.vulnerabilities

    if options.unfixable:
        block_fixable_usns = True
        block_unfixable_usns = False
    elif not options.all:
        block_fixable_usns = False
        block_unfixable_usns = True
    else:
        block_fixable_usns = False
        block_unfixable_usns = False

    usns = []
    for usn_name, usn in sorted(usn_vulnerabilities.items()):
        usn_fix_status = _get_vulnerability_fix_status(
            usn["affected_packages"]
        )

        if (
            usn_fix_status != VulnerabilityStatus.NO_FIX_AVAILABLE
            and block_fixable_usns
        ):
            continue

        if (
            usn_fix_status == VulnerabilityStatus.NO_FIX_AVAILABLE
            and block_unfixable_usns
        ):
            continue

        usns.append(
            USNVulnerabilityResult(
                name=usn_name,
                description=usn["description"],
                published_at=util.parse_rfc3339_date(usn["published_at"]),
                affected_packages=[
                    USNAffectedPackage(
                        name=pkg["name"],
                        current_version=pkg["current_version"],
                        fix_version=pkg["fix_version"],
                        fix_available_from=pkg["fix_available_from"],
                    )
                    for pkg in usn["affected_packages"]
                ],
                fixable=usn_fix_status.value,
                related_cves=usn["related_cves"],
                related_launchpad_bugs=usn["related_launchpad_bugs"],
            )
        )

    return USNVulnerabilitiesResult(
        usns=usns,
        vulnerability_data_published_at=util.parse_rfc3339_date(
            usn_vulnerabilities_result.vulnerability_data_published_at
        ),
        apt_updated_at=(
            get_apt_cache_datetime() if not options.manifest_file else None
        ),
    )


endpoint = APIEndpoint(
    version="v1",
    name="USNVulnerabilities",
    fn=_vulnerabilities,
    options_cls=USNVulnerabilitiesOptions,
)

_doc = {
    "introduced_in": "35",
    "requires_network": True,
    "example_python": """
from uaclient.api.u.pro.security.vulnerabilities.usn.v1 import vulnerabilites,
USNVulnerabilitesOptions

options = USNVulnerabilitiesOptions()
result = vulnerabilities(options)
""",  # noqa: E501
    "result_class": USNVulnerabilitiesResult,
    "ignore_result_classes": [DataObject],
    "extra_result_classes": [
        USNAffectedPackage,
        USNVulnerabilityResult,
    ],
    "exceptions": [],
    "example_cli": "pro api u.pro.security.vulnerabilities.usn.v1",
    "example_json": """
{
    "apt_updated_at": "2024-07-26T20:53:55.708438+00:00",
    "cves": [
      {
        "affected_packages": [
          {
            "current_version": "1.3.1+dfsg-1~ubuntu0.16.04.1",
            "fix_available_from": "esm-infra",
            "fix_version": ".*",
            "name": "libzstd1"
          }
        ],
        "description": "USN description",
        "fixable": "yes",
        "name": "USN-4822-1",
        "published_at": "2024-07-23T20:53:55.708438+00:00"
      }
    ],
    "vulnerability_data_published_at": "2024-07-26T20:53:55.708438+00:00"
}
""",
}
