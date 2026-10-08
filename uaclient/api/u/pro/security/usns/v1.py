import datetime
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

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
    IntDataValue,
    StringDataValue,
    data_dict,
    data_list,
)

# Matches a USN/LSN id of the form USN-<base>-<revision>, capturing the base
# (everything but the trailing revision) and the revision number.
_USN_REVISION_RE = re.compile(r"^(?P<base>.+)-(?P<revision>\d+)$")

# Ubuntu priorities ordered from least to most severe. Used to derive a USN
# priority from the priorities of its related CVEs.
_PRIORITY_RANK = {
    "unknown": 0,
    "negligible": 1,
    "low": 2,
    "medium": 3,
    "high": 4,
    "critical": 5,
}


class USNsOptions(DataObject):
    fields = [
        Field(
            "unfixable",
            BoolDataValue,
            False,
            doc="Show only unfixable USNs.",
        ),
        Field(
            "fixable",
            BoolDataValue,
            False,
            doc="Show only fixable USNs.",
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


class USNAffectedPackage(DataObject):
    fields = [
        Field(
            "name",
            StringDataValue,
            False,
            doc="The USN name",
        ),
        Field(
            "fix_version",
            StringDataValue,
            False,
            doc="The version that fixes the USN for the package",
        ),
        Field(
            "fix_status",
            StringDataValue,
            False,
            doc="The status of the USN fix for the package",
        ),
        Field(
            "fix_origin",
            StringDataValue,
            False,
            doc="The pocket where the fix is available from",
        ),
    ]

    def __init__(
        self,
        name: str,
        fix_version: Optional[str],
        fix_status: str,
        fix_origin: Optional[str],
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
            "usns",
            data_list(USNAffectedPackage),
            doc="The USNs that affect the package",
        ),
    ]

    def __init__(
        self, *, current_version: str, usns: List[USNAffectedPackage]
    ):
        self.current_version = current_version
        self.usns = usns


class USNInfo(DataObject):
    fields = [
        Field(
            "title",
            StringDataValue,
            False,
            doc="The USN title",
        ),
        Field(
            "description",
            StringDataValue,
            False,
            doc="The USN description",
        ),
        Field(
            "published_at",
            DatetimeDataValue,
            False,
            doc="The date this USN revision was published",
        ),
        Field(
            "updated_at",
            DatetimeDataValue,
            False,
            doc="The date of the most recent revision of this USN. Null when this is already the latest revision.",  # noqa: E501
        ),
        Field(
            "revision",
            IntDataValue,
            False,
            doc="The revision number of this USN (the trailing number in the USN id)",  # noqa: E501
        ),
        Field(
            "superseded_by",
            StringDataValue,
            False,
            doc="The USN that immediately supersedes this one, if any",
        ),
        Field(
            "priority",
            StringDataValue,
            False,
            doc="The ubuntu priority for the USN, derived from its related CVEs",  # noqa: E501
        ),
        Field(
            "notes",
            data_list(StringDataValue),
            False,
            doc="A list of notes for the USN",
        ),
        Field(
            "related_cves",
            data_list(StringDataValue),
            False,
            doc="A list of CVEs related to the USN",
        ),
        Field(
            "affected_packages",
            data_list(StringDataValue),
            False,
            doc="A list of installed packages affected by the USN",
        ),
    ]

    def __init__(
        self,
        *,
        title: str,
        description: str,
        published_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        revision: Optional[int] = None,
        superseded_by: Optional[str] = None,
        priority: Optional[str] = None,
        notes: Optional[List[str]] = None,
        related_cves: Optional[List[str]] = None,
        affected_packages: Optional[List[str]] = None
    ):
        self.title = title
        self.description = description
        self.published_at = published_at
        self.updated_at = updated_at
        self.revision = revision
        self.superseded_by = superseded_by
        self.priority = priority
        self.notes = notes
        self.related_cves = related_cves
        self.affected_packages = affected_packages


class USNsResult(DataObject, AdditionalInfo):
    fields = [
        Field(
            "packages",
            data_dict(value_cls=AffectedPackage),
            doc="A dictionary where the keys are installed package names and the values are AffectedPackage objects.",  # noqa
        ),
        Field(
            "usns",
            data_dict(value_cls=USNInfo),
            doc="A dictionary where the keys are USN names and the values are USNInfo objects.",  # noqa
        ),
    ]

    def __init__(
        self,
        *,
        packages: Dict[str, AffectedPackage],
        usns: Dict[str, USNInfo],
        # These fields do not appear on the Fields list
        # because we want to access them in the CLI, but
        # not output them in the API
        vulnerability_data_published_at: datetime.datetime,
        apt_updated_at: Optional[datetime.datetime] = None
    ):
        self.packages = packages
        self.usns = usns
        self.vulnerability_data_published_at = vulnerability_data_published_at
        self.apt_updated_at = apt_updated_at


def _parse_usn_revision(usn_name: str) -> Tuple[Optional[str], Optional[int]]:
    """Split a USN id into its base and revision number.

    ``USN-5376-2`` -> ``("USN-5376", 2)``.
    """
    match = _USN_REVISION_RE.match(usn_name)
    if not match:
        return None, None
    return match.group("base"), int(match.group("revision"))


class USNParser(VulnerabilityParser):
    vulnerability_type = "usns"

    def __init__(self):
        self._supersedence_annotated = False

    def get_package_vulnerabilities(
        self, affected_pkg: Dict[str, Any]
    ) -> Dict[str, Any]:
        # At the package level the USN data lives under the
        # "ubuntu_security_notices" key, even though the security_issues
        # section and the API output use "usns".
        return affected_pkg.get("ubuntu_security_notices", {})

    def _annotate_supersedence(self, all_usns: Dict[str, Any]) -> None:
        """Annotate each USN with its supersedence/revision information.

        USNs are immutable once published: an "update" is issued as a new USN
        that shares the same base number with an incremented revision (e.g.
        ``USN-5376-2`` is superseded by ``USN-5376-3``). We use that to
        populate, on each USN info dict:

        - ``superseded_by``: the id of the immediately following revision.
        - ``updated_at``: the ``published_at`` of the most recent revision in
          the family (``None`` when this is already the latest revision).
        """
        if self._supersedence_annotated:
            return
        self._supersedence_annotated = True

        families = defaultdict(list)  # type: Dict[str, List[Tuple[int, str]]]
        for usn_name in all_usns:
            base, revision = _parse_usn_revision(usn_name)
            if base is None or revision is None:
                continue
            families[base].append((revision, usn_name))

        for revisions in families.values():
            revisions.sort()
            _, latest_name = revisions[-1]
            latest_published_at = (all_usns.get(latest_name, {}) or {}).get(
                "published_at"
            )

            for index, (_, usn_name) in enumerate(revisions):
                usn_info = all_usns.get(usn_name)
                if not isinstance(usn_info, dict):
                    continue

                is_latest = usn_name == latest_name
                usn_info["superseded_by"] = (
                    None if is_latest else revisions[index + 1][1]
                )
                usn_info["updated_at"] = (
                    None if is_latest else latest_published_at
                )

    def _post_process_vulnerability_info(
        self,
        vulnerability_info: Dict[str, Any],
        vulnerabilities_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not isinstance(vulnerability_info, dict):
            return {}

        self._annotate_supersedence(
            vulnerabilities_data.get("security_issues", {}).get("usns", {})
        )

        # The USN data does not carry an ubuntu priority. We derive one from
        # the most severe priority across its related CVEs.
        cves_info = vulnerabilities_data.get("security_issues", {}).get(
            "cves", {}
        )

        priority = None
        for related_cve in vulnerability_info.get("related_cves", []):
            cve_priority = cves_info.get(related_cve, {}).get(
                "ubuntu_priority"
            )
            if cve_priority is None:
                continue
            if priority is None or _PRIORITY_RANK.get(
                cve_priority, 0
            ) > _PRIORITY_RANK.get(priority, 0):
                priority = cve_priority

        vulnerability_info["priority"] = priority

        return vulnerability_info


def usn_status_match_options(usn, options) -> bool:
    is_fixable = usn.get("fix_version") and usn.get("fix_origin")

    if options.unfixable and is_fixable:
        return False
    elif options.fixable and not is_fixable:
        return False
    return True


def usns(
    options: USNsOptions,
) -> USNsResult:
    return _usns(options, UAConfig())


def _parse_vulnerabilities(
    options: USNsOptions,
    vulnerabilities: Dict[str, Any],
    vulnerability_data_published_at: str,
) -> USNsResult:
    packages = {}  # type: Dict[str, AffectedPackage]
    # For each allowed USN, collect the installed packages it affects.
    affected_packages = {}  # type: Dict[str, List[str]]
    for pkg_name, package_info in sorted(
        vulnerabilities.get("packages", {}).items()
    ):
        pkg_usns = []
        for usn in sorted(
            package_info.get("usns", []), key=lambda usn: usn["name"]
        ):
            if usn_status_match_options(usn, options):
                pkg_usns.append(
                    USNAffectedPackage(
                        name=usn["name"],
                        fix_version=usn["fix_version"],
                        # The USN data has no per-package status. A USN always
                        # represents a published fix, so when a fix version is
                        # available we report it as "fixed". The generic parser
                        # sets "unknown" for package-transition edge cases.
                        fix_status=usn["fix_status"] or "fixed",
                        fix_origin=usn["fix_origin"],
                    )
                )
                affected_packages.setdefault(usn["name"], []).append(pkg_name)

        if pkg_usns:
            packages[pkg_name] = AffectedPackage(
                current_version=package_info["current_version"],
                usns=pkg_usns,
            )

    usns = {
        usn_name: USNInfo(
            title=usn.get("title", ""),
            description=usn.get("description", ""),
            published_at=(
                util.parse_rfc3339_date(usn["published_at"])
                if usn.get("published_at")
                else None
            ),
            updated_at=(
                util.parse_rfc3339_date(usn["updated_at"])
                if usn.get("updated_at")
                else None
            ),
            revision=_parse_usn_revision(usn_name)[1],
            superseded_by=usn.get("superseded_by"),
            priority=usn.get("priority"),
            notes=usn.get("notes", []),
            related_cves=usn.get("related_cves", []),
            affected_packages=sorted(affected_packages.get(usn_name, [])),
        )
        for usn_name, usn in sorted(
            vulnerabilities.get("vulnerabilities", {}).items(),
            key=lambda v: v[0],
        )
        if usn_name in affected_packages
    }

    return USNsResult(
        packages=packages,
        usns=usns,
        vulnerability_data_published_at=util.parse_rfc3339_date(
            vulnerability_data_published_at
        ),
        apt_updated_at=get_apt_cache_datetime(),
    )


def _usns(
    options: USNsOptions,
    cfg: UAConfig,
) -> USNsResult:
    """
    This endpoint shows the USN vulnerabilities in the system.
    By default, this API will show all USNs that affect the system.
    """

    # By default we return all affected USNs. If a user provides
    # both options, we just switch to the default approach
    if options.unfixable and options.fixable:
        options.unfixable = False
        options.fixable = False

    series = system.get_release_info().series

    usn_vulnerabilities_result = get_vulnerabilities(
        parser=USNParser(),
        cfg=cfg,
        series=series,
    )

    usn_vulnerabilities = usn_vulnerabilities_result.vulnerabilities_info

    return _parse_vulnerabilities(
        options=options,
        vulnerabilities=usn_vulnerabilities,
        vulnerability_data_published_at=usn_vulnerabilities_result.vulnerability_data_published_at,  # noqa
    )


endpoint = APIEndpoint(
    version="v1",
    name="USNs",
    fn=_usns,
    options_cls=USNsOptions,
)

_doc = {
    "introduced_in": "38",
    "requires_network": True,
    "example_python": """
from uaclient.api.u.pro.security.usns.v1 import usns, USNsOptions

options = USNsOptions()
result = usns(options)
""",  # noqa: E501
    "result_class": USNsResult,
    "ignore_result_classes": [DataObject],
    "exceptions": [],
    "example_cli": "pro api u.pro.security.usns.v1",
    "example_json": """
{
    "usns": {
      "USN-6491-1": {
        "title": "AccountsService vulnerability",
        "description": "description example",
        "notes": [],
        "priority": "medium",
        "published_at": ".*",
        "updated_at": null,
        "revision": 1,
        "superseded_by": null,
        "related_cves": ["CVE-2023-5678"],
        "affected_packages": ["accountsservice", "libaccountsservice0"]
      }
    },
    "packages": {
      "accountsservice": {
        "current_version": "0.6.40-2ubuntu11.6",
        "usns": [
          {
            "fix_origin": "esm-infra",
            "fix_status": "fixed",
            "fix_version": "0.6.40-2ubuntu11.6+esm1",
            "name": "USN-6491-1"
          }
        ]
      },
      "libaccountsservice0": {
        "current_version": "0.6.40-2ubuntu11.6",
        "usns": [
          {
            "fix_origin": "esm-infra",
            "fix_status": "fixed",
            "fix_version": "0.6.40-2ubuntu11.6+esm1",
            "name": "USN-6491-1"
          }
        ]
      }
    },
}
""",
}
