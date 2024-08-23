import copy
import enum
import socket
from collections import defaultdict
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from uaclient import apt, exceptions, livepatch, messages, system, util
from uaclient.http import serviceclient

CVE_OR_USN_REGEX = (
    r"((CVE|cve)-\d{4}-\d{4,7}$|(USN|usn|LSN|lsn)-\d{1,5}-\d{1,2}$)"
)

API_V1_CVES = "cves.json"
API_V1_CVE_TMPL = "cves/{cve}.json"
API_V1_NOTICES = "notices.json"
API_V1_NOTICE_TMPL = "notices/{notice}.json"

STANDARD_UPDATES_POCKET = "standard-updates"
ESM_INFRA_POCKET = "esm-infra"
ESM_APPS_POCKET = "esm-apps"

BinaryPackageFix = NamedTuple(
    "BinaryPackageFix",
    [
        ("source_pkg", str),
        ("binary_pkg", str),
        ("fixed_version", str),
    ],
)

UnfixedPackage = NamedTuple(
    "UnfixedPackage",
    [
        ("pkg", str),
        ("unfixed_reason", str),
    ],
)


class FixStatus(enum.Enum):
    """
    An enum to represent the system status after fix operation
    """

    class _Value:
        def __init__(self, value: int, msg: str):
            self.value = value
            self.msg = msg

    SYSTEM_NON_VULNERABLE = _Value(0, "fixed")
    SYSTEM_NOT_AFFECTED = _Value(0, "not-affected")
    SYSTEM_STILL_VULNERABLE = _Value(1, "still-affected")
    SYSTEM_VULNERABLE_UNTIL_REBOOT = _Value(2, "affected-until-reboot")

    @property
    def exit_code(self):
        return self.value.value

    def __str__(self):
        return self.value.msg


class UASecurityClient(serviceclient.UAServiceClient):

    url_timeout = 20
    cfg_url_base_attr = "security_url"

    def _get_query_params(
        self, query_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update query params with data from feature config.
        """
        extra_security_params = self.cfg.cfg.get("features", {}).get(
            "extra_security_params", {}
        )

        if query_params:
            query_params.update(extra_security_params)
            return query_params

        return extra_security_params

    @util.retry(socket.timeout, retry_sleeps=[1, 3, 5])
    def request_url(
        self, path, data=None, headers=None, method=None, query_params=None
    ):
        query_params = self._get_query_params(query_params)
        return super().request_url(
            path=path,
            data=data,
            headers=headers,
            method=method,
            query_params=query_params,
            log_response_body=False,
        )

    def get_cves(
        self,
        query: Optional[str] = None,
        priority: Optional[str] = None,
        package: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        component: Optional[str] = None,
        version: Optional[str] = None,
        status: Optional[List[str]] = None,
    ) -> List["CVE"]:
        """Query to match multiple-CVEs.

        @return: List of CVE instances based on the the JSON response.
        """
        query_params = {
            "q": query,
            "priority": priority,
            "package": package,
            "limit": limit,
            "offset": offset,
            "component": component,
            "version": version,
            "status": status,
        }
        response = self.request_url(API_V1_CVES, query_params=query_params)
        if response.code != 200:
            raise exceptions.SecurityAPIError(
                url=API_V1_CVES, code=response.code, body=response.body
            )
        return [
            CVE(client=self, response=cve_md) for cve_md in response.json_list
        ]

    def get_cve(self, cve_id: str) -> "CVE":
        """Query to match single-CVE.

        @return: CVE instance for JSON response from the Security API.
        """
        url = API_V1_CVE_TMPL.format(cve=cve_id)
        response = self.request_url(url)
        if response.code != 200:
            raise exceptions.SecurityAPIError(
                url=url, code=response.code, body=response.body
            )
        return CVE(client=self, response=response.json_dict)

    def get_notices(
        self,
        cves: Optional[str] = None,
        release: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order: Optional[str] = None,
    ) -> List["USN"]:
        """Query to match multiple-USNs.

        @return: Sorted list of USN instances based on the the JSON response.
        """
        query_params = {
            "cves": cves,
            "release": release,
            "limit": limit,
            "offset": offset,
            "order": order,
        }
        response = self.request_url(API_V1_NOTICES, query_params=query_params)
        if response.code != 200:
            raise exceptions.SecurityAPIError(
                url=API_V1_NOTICES, code=response.code, body=response.body
            )

        return sorted(
            [
                USN(client=self, response=usn_md)
                for usn_md in response.json_dict.get("notices", [])
                if (cves is None or cves in usn_md.get("cves_ids", []))
                and usn_md.get("id", "").startswith("USN-")
            ],
            key=lambda x: x.id,
        )

    def get_notice(self, notice_id: str) -> "USN":
        """Query to match single-USN.

        @return: USN instance representing the JSON response.
        """
        url = API_V1_NOTICE_TMPL.format(notice=notice_id)
        response = self.request_url(url)
        if response.code != 200:
            raise exceptions.SecurityAPIError(
                url=url, code=response.code, body=response.body
            )
        return USN(client=self, response=response.json_dict)


# Model for Security API responses
class CVEPackageStatus:
    """Class representing specific CVE PackageStatus on an Ubuntu series"""

    def __init__(self, cve_response: Dict[str, Any]):
        self.response = cve_response

    @property
    def description(self):
        return self.response["description"]

    @property
    def fixed_version(self):
        return self.description

    @property
    def pocket(self):
        return self.response["pocket"]

    @property
    def release_codename(self):
        return self.response["release_codename"]

    @property
    def status(self):
        return self.response["status"]

    @property
    def status_message(self):
        if self.status == "needed":
            return messages.SECURITY_CVE_STATUS_NEEDED
        elif self.status == "needs-triage":
            return messages.SECURITY_CVE_STATUS_TRIAGE
        elif self.status == "pending":
            return messages.SECURITY_CVE_STATUS_PENDING
        elif self.status in ("ignored", "deferred"):
            return messages.SECURITY_CVE_STATUS_IGNORED
        elif self.status == "DNE":
            return messages.SECURITY_CVE_STATUS_DNE
        elif self.status == "not-affected":
            return messages.SECURITY_CVE_STATUS_NOT_AFFECTED
        elif self.status == "released":
            return messages.SECURITY_FIX_RELEASE_STREAM.format(
                fix_stream=self.pocket_source
            )
        return messages.SECURITY_CVE_STATUS_UNKNOWN.format(status=self.status)

    @property
    def requires_ua(self) -> bool:
        """Return True if the package requires an active Pro subscription."""
        return bool(
            self.pocket_source
            != messages.SECURITY_UBUNTU_STANDARD_UPDATES_POCKET
        )

    @property
    def pocket_source(self):
        """Human-readable string representing where the fix is published."""
        if self.pocket == "esm-infra":
            fix_source = messages.SECURITY_UA_INFRA_POCKET
        elif self.pocket == "esm-apps":
            fix_source = messages.SECURITY_UA_APPS_POCKET
        elif self.pocket in ("updates", "security"):
            fix_source = messages.SECURITY_UBUNTU_STANDARD_UPDATES_POCKET
        else:
            # TODO(GH: #1376 drop this when esm* pockets supplied by API)
            if "esm" in self.fixed_version:
                fix_source = messages.SECURITY_UA_INFRA_POCKET
            else:
                fix_source = messages.SECURITY_UBUNTU_STANDARD_UPDATES_POCKET
        return fix_source


class CVE:
    """Class representing CVE response from the SecurityClient"""

    def __init__(self, client: UASecurityClient, response: Dict[str, Any]):
        self.response = response
        self.client = client

    def __eq__(self, other) -> bool:
        if not isinstance(other, CVE):
            return False
        return self.response == other.response

    @property
    def id(self):
        return self.response.get("id", "UNKNOWN_CVE_ID").upper()

    @property
    def notices_ids(self) -> List[str]:
        return self.response.get("notices_ids", [])

    @property
    def notices(self) -> List["USN"]:
        """Return a list of USN instances from API response 'notices'.

        Cache the value to avoid extra work on multiple calls.
        """
        if not hasattr(self, "_notices"):
            self._notices = sorted(
                [
                    USN(self.client, notice)
                    for notice in self.response.get("notices", [])
                    if notice and notice.get("id", "").startswith("USN-")
                ],
                key=lambda n: n.id,
                reverse=True,
            )
        return self._notices

    @property
    def description(self):
        return self.response.get("description")

    @property
    def packages_status(self) -> Dict[str, CVEPackageStatus]:
        """Dict of package status dicts for the current Ubuntu series.

        Top-level keys are source packages names and each value is a
        CVEPackageStatus object
        """
        if hasattr(self, "_packages_status"):
            return self._packages_status  # type: ignore
        self._packages_status = {}
        series = system.get_release_info().series
        for package in self.response["packages"]:
            for pkg_status in package["statuses"]:
                if pkg_status["release_codename"] == series:
                    self._packages_status[package["name"]] = CVEPackageStatus(
                        pkg_status
                    )
        return self._packages_status


class USN:
    """Class representing USN response from the SecurityClient"""

    def __init__(self, client: UASecurityClient, response: Dict[str, Any]):
        self.response = response
        self.client = client

    def __eq__(self, other) -> bool:
        if not isinstance(other, USN):
            return False
        return self.response == other.response

    @property
    def id(self) -> str:
        return self.response.get("id", "UNKNOWN_USN_ID").upper()

    @property
    def cves_ids(self) -> List[str]:
        """List of CVE IDs related to this USN."""
        return self.response.get("cves_ids", [])

    @property
    def cves(self) -> List[CVE]:
        """List of CVE instances based on API response 'cves' key.

        Cache the values to avoid extra work for multiple call-sites.
        """
        if not hasattr(self, "_cves"):
            self._cves = sorted(
                [
                    CVE(self.client, cve)
                    for cve in self.response.get("cves", [])
                ],
                key=lambda n: n.id,
                reverse=True,
            )  # type: List[CVE]
        return self._cves

    @property
    def title(self):
        return self.response.get("title")

    @property
    def references(self):
        return self.response.get("references")

    @property
    def release_packages(self) -> Dict[str, Dict[str, Dict[str, str]]]:
        """Binary package information available for this release.


        Reformat the USN.release_packages response to key it based on source
        package name and related binary package names.

        :return: Dict keyed by source package name. The second-level key will
            be binary package names generated from that source package and the
            values will be the dict response from USN.release_packages for
            that binary package. The binary metadata contains the following
            keys: name, version.
            Optional additional keys: pocket and component.
        """
        if hasattr(self, "_release_packages"):
            return self._release_packages
        series = system.get_release_info().series
        self._release_packages = {}  # type: Dict[str, Dict[str, Any]]
        # Organize source and binary packages under a common source package key
        for pkg in self.response.get("release_packages", {}).get(series, []):
            if pkg.get("is_source"):
                # Create a "source" key under src_pkg_name with API response
                if pkg["name"] in self._release_packages:
                    if "source" in self._release_packages[pkg["name"]]:
                        raise exceptions.SecurityAPIMetadataError(
                            error_msg=(
                                "{usn} metadata defines duplicate source"
                                " packages {pkg}"
                            ).format(usn=self.id, pkg=pkg["name"]),
                            issue=self.id,
                            extra_info="",
                        )
                    self._release_packages[pkg["name"]]["source"] = pkg
                else:
                    self._release_packages[pkg["name"]] = {"source": pkg}
            else:
                # is_source == False or None, then this is a binary package.
                # If processed before a source item, the top-level key will
                # not exist yet.
                # TODO(GH: 1465: determine if this is expected on kern pkgs)
                if not pkg.get("source_link"):
                    raise exceptions.SecurityAPIMetadataError(
                        error_msg=(
                            "{issue} metadata does not define release_packages"
                            " source_link for {bin_pkg}."
                        ).format(issue=self.id, bin_pkg=pkg["name"]),
                        issue=self.id,
                        extra_info="",
                    )
                elif "/" not in pkg["source_link"]:
                    raise exceptions.SecurityAPIMetadataError(
                        error_msg=(
                            "{issue} metadata has unexpected release_packages"
                            " source_link value for {bin_pkg}: {link}"
                        ).format(
                            issue=self.id,
                            bin_pkg=pkg["name"],
                            link=pkg["source_link"],
                        ),
                        issue=self.id,
                        extra_info="",
                    )
                source_pkg_name = pkg["source_link"].split("/")[-1]
                if source_pkg_name not in self._release_packages:
                    self._release_packages[source_pkg_name] = {}
                self._release_packages[source_pkg_name][pkg["name"]] = pkg
        return self._release_packages


def get_cve_affected_source_packages_status(
    cve: CVE, installed_packages: Dict[str, Dict[str, str]]
) -> Dict[str, CVEPackageStatus]:
    """Get a dict of any CVEPackageStatuses affecting this Ubuntu release.

    :return: Dict of active CVEPackageStatus keyed by source package names.
    """
    affected_pkg_versions = {}
    for source_pkg, package_status in cve.packages_status.items():
        if package_status.status == "not-affected":
            continue
        if source_pkg in installed_packages:
            affected_pkg_versions[source_pkg] = package_status
    return affected_pkg_versions


def query_installed_source_pkg_versions() -> Dict[str, Dict[str, str]]:
    """Return a dict of all source packages installed on the system.

    The dict keys will be source package name: "krb5". The value will be a dict
    with keys binary_pkg and version.
    """
    status_field = "${db:Status-Status}"
    out, _err = system.subp(
        [
            "dpkg-query",
            "-f=${Package},${Source},${Version}," + status_field + "\n",
            "-W",
        ]
    )
    installed_packages = {}  # type: Dict[str, Dict[str, str]]
    for pkg_line in out.splitlines():
        pkg_name, source_pkg_name, pkg_version, status = pkg_line.split(",")
        if not source_pkg_name:
            # some package don't define the Source
            source_pkg_name = pkg_name
        if "installed" not in status:
            continue
        if source_pkg_name in installed_packages:
            installed_packages[source_pkg_name][pkg_name] = pkg_version
        else:
            installed_packages[source_pkg_name] = {pkg_name: pkg_version}
    return installed_packages


def get_related_usns(usn, client):
    """For a give usn, get the related USNs for it.

    For each CVE associated with the given USN, we capture
    other USNs that are related to the CVE. We consider those
    USNs related to the original USN.
    """

    # If the usn does not have any associated cves on it,
    # we cannot establish a relation between USNs
    if not usn.cves:
        return []

    related_usns = {}
    for cve in usn.cves:
        for related_usn_id in cve.notices_ids:
            # We should ignore any other item that is not a USN
            # For example, LSNs
            if not related_usn_id.startswith("USN-"):
                continue
            if related_usn_id == usn.id:
                continue
            if related_usn_id not in related_usns:
                related_usns[related_usn_id] = client.get_notice(
                    notice_id=related_usn_id
                )

    return list(sorted(related_usns.values(), key=lambda x: x.id))


def get_affected_packages_from_cves(cves, installed_packages):
    affected_pkgs = {}  # type: Dict[str, CVEPackageStatus]

    for cve in cves:
        for pkg_name, pkg_status in get_cve_affected_source_packages_status(
            cve, installed_packages
        ).items():
            if pkg_name not in affected_pkgs:
                affected_pkgs[pkg_name] = pkg_status
            else:
                current_ver = affected_pkgs[pkg_name].fixed_version
                if (
                    apt.version_compare(current_ver, pkg_status.fixed_version)
                    > 0
                ):
                    affected_pkgs[pkg_name] = pkg_status

    return affected_pkgs


def get_affected_packages_from_usn(usn, installed_packages):
    affected_pkgs = {}  # type: Dict[str, CVEPackageStatus]
    for pkg_name, pkg_info in usn.release_packages.items():
        if pkg_name not in installed_packages:
            continue

        cve_response = defaultdict(str)
        cve_response["status"] = "released"
        # Here we are assuming that the pocket will be the same one across
        # all the different binary packages.
        all_pockets = {
            pkg_bin_info["pocket"]
            for _, pkg_bin_info in pkg_info.items()
            if pkg_bin_info.get("pocket")
        }
        if not all_pockets:
            raise exceptions.SecurityAPIMetadataError(
                error_msg=(
                    "{} metadata defines no pocket information for "
                    "any release packages."
                ).format(usn.id),
                issue=usn.id,
                extra_info="",
            )
        cve_response["pocket"] = all_pockets.pop()

        affected_pkgs[pkg_name] = CVEPackageStatus(cve_response=cve_response)

    return affected_pkgs


def get_usn_affected_packages_status(
    usn: USN, installed_packages: Dict[str, Dict[str, str]]
) -> Dict[str, CVEPackageStatus]:
    """Walk CVEs related to a USN and return a dict of all affected packages.

    :return: Dict keyed on source package name, with active CVEPackageStatus
        for the current Ubuntu release.
    """
    if usn.cves:
        return get_affected_packages_from_cves(usn.cves, installed_packages)
    else:
        return get_affected_packages_from_usn(usn, installed_packages)


def override_usn_release_package_status(
    pkg_status: CVEPackageStatus,
    usn_src_released_pkgs: Dict[str, Dict[str, str]],
) -> CVEPackageStatus:
    """Parse release status based on both pkg_status and USN.release_packages.

    Since some source packages in universe are not represented in
    CVEPackageStatus, rely on presence of such source packages in
    usn_src_released_pkgs to represent package as a "released" status.

    :param pkg_status: the CVEPackageStatus for this source package.
    :param usn_src_released_pkgs: The USN.release_packages representing only
       this source package. Normally, release_packages would have data on
       multiple source packages.

    :return: Tuple of:
        human-readable status message, boolean whether released,
        boolean whether the fix requires access to UA
    """

    usn_pkg_status = copy.deepcopy(pkg_status)
    if usn_src_released_pkgs and usn_src_released_pkgs.get("source"):
        usn_pkg_status.response["status"] = "released"
        usn_pkg_status.response["description"] = usn_src_released_pkgs[
            "source"
        ]["version"]
        for pkg_name, usn_released_pkg in usn_src_released_pkgs.items():
            # Copy the pocket from any valid binary package
            pocket = usn_released_pkg.get("pocket")
            if pocket:
                usn_pkg_status.response["pocket"] = pocket
                break
    return usn_pkg_status


def group_by_usn_package_status(affected_pkg_status, usn_released_pkgs):
    status_groups = {}  # type: Dict[str, List[Tuple[str, CVEPackageStatus]]]
    for src_pkg, pkg_status in sorted(affected_pkg_status.items()):
        usn_released_src = usn_released_pkgs.get(src_pkg, {})
        usn_pkg_status = override_usn_release_package_status(
            pkg_status, usn_released_src
        )
        status_group = usn_pkg_status.status.replace("ignored", "deferred")
        if status_group not in status_groups:
            status_groups[status_group] = []
        status_groups[status_group].append((src_pkg, usn_pkg_status))
    return status_groups


def merge_usn_released_binary_package_versions(
    usns: List[USN], beta_pockets: Dict[str, bool]
) -> Dict[str, Dict[str, Dict[str, str]]]:
    """Walk related USNs, merging the released binary package versions.

    For each USN, iterate over release_packages to collect released binary
        package names and required fix version. If multiple related USNs
        require different version fixes to the same binary package, track the
        maximum version required across all USNs.

    :param usns: List of USN response instances from which to calculate merge.
    :param beta_pockets: Dict keyed on service name: esm-infra, esm-apps
        the values of which will be true of USN response instances
        from which to calculate merge.

    :return: Dict keyed by source package name. Under each source package will
        be a dict with binary package name as keys and binary package metadata
        as the value.
    """
    usn_pkg_versions = {}
    for usn in usns:
        # Aggregate USN.release_package binary versions into usn_pkg_versions
        for src_pkg, binary_pkg_versions in usn.release_packages.items():
            public_bin_pkg_versions = {
                bin_pkg_name: bin_pkg_md
                for bin_pkg_name, bin_pkg_md in binary_pkg_versions.items()
                if False
                is beta_pockets.get(bin_pkg_md.get("pocket", "None"), False)
            }
            if src_pkg not in usn_pkg_versions and public_bin_pkg_versions:
                usn_pkg_versions[src_pkg] = public_bin_pkg_versions
            elif src_pkg in usn_pkg_versions:
                # Since src_pkg exists, only record this USN's binary version
                # when it is greater than the previous version in usn_src_pkg.
                usn_src_pkg = usn_pkg_versions[src_pkg]
                for bin_pkg, binary_pkg_md in public_bin_pkg_versions.items():
                    if bin_pkg not in usn_src_pkg:
                        usn_src_pkg[bin_pkg] = binary_pkg_md
                    else:
                        prev_version = usn_src_pkg[bin_pkg]["version"]
                        current_version = binary_pkg_md["version"]
                        if (
                            apt.version_compare(current_version, prev_version)
                            > 0
                        ):
                            # binary_version is greater than prev_version
                            usn_src_pkg[bin_pkg] = binary_pkg_md
    return usn_pkg_versions


def _check_cve_fixed_by_livepatch(
    issue_id: str,
) -> Tuple[Optional[FixStatus], Optional[str]]:
    # Check livepatch status for CVE in fixes before checking CVE api
    lp_status = livepatch.status()
    if (
        lp_status is not None
        and lp_status.livepatch is not None
        and lp_status.livepatch.fixes is not None
    ):
        for fix in lp_status.livepatch.fixes:
            if fix.name == issue_id.lower() and fix.patched:
                version = lp_status.livepatch.version or "N/A"
                return (FixStatus.SYSTEM_NON_VULNERABLE, version)

    return (None, None)


def status_message(status, pocket_source: Optional[str] = None):
    if status == "needed":
        return messages.SECURITY_CVE_STATUS_NEEDED
    elif status == "needs-triage":
        return messages.SECURITY_CVE_STATUS_TRIAGE
    elif status == "pending":
        return messages.SECURITY_CVE_STATUS_PENDING
    elif status in ("ignored", "deferred"):
        return messages.SECURITY_CVE_STATUS_IGNORED
    elif status == "DNE":
        return messages.SECURITY_CVE_STATUS_DNE
    elif status == "not-affected":
        return messages.SECURITY_CVE_STATUS_NOT_AFFECTED
    elif status == "released" and pocket_source:
        return messages.SECURITY_FIX_RELEASE_STREAM.format(
            fix_stream=pocket_source
        )
    return messages.SECURITY_CVE_STATUS_UNKNOWN.format(status=status)


def get_expected_overall_status(
    current_fix_status: str, fix_status: str
) -> str:
    if not current_fix_status:
        return fix_status

    if fix_status in (
        FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
        FixStatus.SYSTEM_NOT_AFFECTED.value.msg,
    ):
        if (
            current_fix_status == FixStatus.SYSTEM_NOT_AFFECTED.value.msg
            and current_fix_status != fix_status
        ):
            return fix_status
        else:
            return current_fix_status
    else:
        # This means the system is still affected and we must
        # priotize this as the global state
        return fix_status
