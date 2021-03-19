import copy
import itertools
import logging
import os
import socket

from uaclient import apt
from uaclient.config import UAConfig
from uaclient.clouds.identity import (
    CLOUD_TYPE_TO_TITLE,
    PRO_CLOUDS,
    get_cloud_type,
)
from uaclient import exceptions
from uaclient import status
from uaclient import serviceclient
from uaclient import util

try:
    from typing import Any, Dict, List, Optional, Tuple  # noqa: F401
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass


CVE_OR_USN_REGEX = (
    r"((CVE|cve)-\d{4}-\d{4,7}$|(USN|usn|LSN|lsn)-\d{1,5}-\d{1,2}$)"
)

API_V1_CVES = "cves.json"
API_V1_CVE_TMPL = "cves/{cve}.json"
API_V1_NOTICES = "notices.json"
API_V1_NOTICE_TMPL = "notices/{notice}.json"


class SecurityAPIError(util.UrlError):
    def __init__(self, e, error_response):
        super().__init__(e, e.code, e.headers, e.url)
        self.message = error_response.get("message", "")

    def __contains__(self, error_code):
        return bool(error_code in self.message)

    def __get__(self, error_str, default=None):
        if error_str in self.message:
            return self.message
        return default

    def __str__(self):
        prefix = super().__str__()
        details = [self.message]
        if details:
            return prefix + ": [" + self.url + "] " + ", ".join(details)
        return prefix + ": [" + self.url + "]"


class UASecurityClient(serviceclient.UAServiceClient):

    url_timeout = 20
    cfg_url_base_attr = "security_url"
    api_error_cls = SecurityAPIError

    def _get_query_params(
        self, query_params: "Dict[str, Any]"
    ) -> "Dict[str, Any]":
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
        )

    def get_cves(
        self,
        query: "Optional[str]" = None,
        priority: "Optional[str]" = None,
        package: "Optional[str]" = None,
        limit: "Optional[int]" = None,
        offset: "Optional[int]" = None,
        component: "Optional[str]" = None,
        version: "Optional[str]" = None,
        status: "Optional[List[str]]" = None,
    ) -> "List[CVE]":
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
        cves_response, _headers = self.request_url(
            API_V1_CVES, query_params=query_params
        )
        return [CVE(client=self, response=cve_md) for cve_md in cves_response]

    def get_cve(self, cve_id: str) -> "CVE":
        """Query to match single-CVE.

        @return: CVE instance for JSON response from the Security API.
        """
        cve_response, _headers = self.request_url(
            API_V1_CVE_TMPL.format(cve=cve_id)
        )
        return CVE(client=self, response=cve_response)

    def get_notices(
        self,
        details: "Optional[str]" = None,
        release: "Optional[str]" = None,
        limit: "Optional[int]" = None,
        offset: "Optional[int]" = None,
        order: "Optional[str]" = None,
    ) -> "List[USN]":
        """Query to match multiple-USNs.

        @return: Sorted list of USN instances based on the the JSON response.
        """
        query_params = {
            "details": details,
            "release": release,
            "limit": limit,
            "offset": offset,
            "order": order,
        }
        usns_response, _headers = self.request_url(
            API_V1_NOTICES, query_params=query_params
        )
        return sorted(
            [
                USN(client=self, response=usn_md)
                for usn_md in usns_response.get("notices", [])
            ],
            key=lambda x: x.id,
        )

    def get_notice(self, notice_id: str) -> "USN":
        """Query to match single-USN.

        @return: USN instance representing the JSON response.
        """
        notice_response, _headers = self.request_url(
            API_V1_NOTICE_TMPL.format(notice=notice_id)
        )
        return USN(client=self, response=notice_response)


# Model for Security API responses
class CVEPackageStatus:
    """Class representing specific CVE PackageStatus on an Ubuntu series"""

    def __init__(self, cve_response: "Dict[str, Any]"):
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
            return "Sorry, no fix is available yet."
        elif self.status == "needs-triage":
            return "Ubuntu security engineers are investigating this issue."
        elif self.status == "pending":
            return "A fix is coming soon. Try again tomorrow."
        elif self.status in ("ignored", "deferred"):
            return "Sorry, no fix is available."
        elif self.status == "DNE":
            return "Source package does not exist on this release."
        elif self.status == "released":
            return status.MESSAGE_SECURITY_FIX_RELEASE_STREAM.format(
                fix_stream=self.pocket_source
            )
        return "UNKNOWN: {}".format(self.status)

    @property
    def requires_ua(self) -> bool:
        """Return True if the package requires an active UA subscription."""
        return bool(self.pocket_source != "Ubuntu standard updates")

    @property
    def pocket_source(self):
        """Human-readable string representing where the fix is published."""
        if self.pocket == "esm-infra":
            fix_source = "UA Infra"
        elif self.pocket == "esm-apps":
            fix_source = "UA Apps"
        elif self.pocket in ("updates", "security"):
            fix_source = "Ubuntu standard updates"
        else:
            # TODO(GH: #1376 drop this when esm* pockets supplied by API)
            if "esm" in self.fixed_version:
                fix_source = "UA Infra"
            else:
                fix_source = "Ubuntu standard updates"
        return fix_source


class CVE:
    """Class representing CVE response from the SecurityClient"""

    def __init__(self, client: UASecurityClient, response: "Dict[str, Any]"):
        self.response = response
        self.client = client

    @property
    def id(self):
        return self.response.get("id", "UNKNOWN_CVE_ID").upper()

    def get_notices_metadata(self):
        if hasattr(self, "_notices"):
            return self._notices
        self._notices = []
        for notice_id in sorted(self.notice_ids, reverse=True):
            try:
                self._notices.append(
                    self.client.get_notice(notice_id=notice_id)
                )
            except SecurityAPIError as e:
                logging.debug(
                    "Cannot collect USN info for {}: {}".format(
                        notice_id, str(e)
                    )
                )
        return self._notices

    def get_url_header(self):
        """Return a string representing the URL for this cve."""
        title = self.description
        for notice in self.get_notices_metadata():
            # Only look at the most recent USN title
            title = notice.title
            break
        lines = [
            "{issue}: {title}".format(issue=self.id, title=title),
            "https://ubuntu.com/security/{}".format(self.id),
        ]
        return "\n".join(lines)

    @property
    def notice_ids(self):
        return self.response.get("notices", [])

    @property
    def description(self):
        return self.response.get("description")

    @property
    def packages_status(self) -> "Dict[str, CVEPackageStatus]":
        """Dict of package status dicts for the current Ubuntu series.

        Top-level keys are source packages names and each value is a
        CVEPackageStatus object
        """
        if hasattr(self, "_packages_status"):
            return self._packages_status  # type: ignore
        self._packages_status = {}
        series = util.get_platform_info()["series"]
        for package in self.response["packages"]:
            for pkg_status in package["statuses"]:
                if pkg_status["release_codename"] == series:
                    self._packages_status[package["name"]] = CVEPackageStatus(
                        pkg_status
                    )
        return self._packages_status


class USN:
    """Class representing USN response from the SecurityClient"""

    def __init__(self, client: UASecurityClient, response: "Dict[str, Any]"):
        self.response = response
        self.client = client

    @property
    def id(self) -> str:
        return self.response.get("id", "UNKNOWN_USN_ID").upper()

    @property
    def cve_ids(self) -> "List[str]":
        """List of CVE IDs related to this USN."""
        return self.response.get("cves", [])

    @property
    def title(self):
        return self.response.get("title")

    def get_cves_metadata(self) -> "List[CVE]":
        if hasattr(self, "_cves"):
            return self._cves
        self._cves = []  # type: List[CVE]
        for cve_id in sorted(self.cve_ids, reverse=True):
            self._cves.append(self.client.get_cve(cve_id=cve_id))
        return self._cves

    def get_url_header(self):
        """Return a string representing the URL for this notice."""
        lines = [
            "{issue}: {title}".format(issue=self.id, title=self.title),
            "Found CVEs: {}".format(
                ", ".join(sorted(self.cve_ids, reverse=True))
            ),
        ]
        for cve in self.cve_ids:
            lines.append("https://ubuntu.com/security/{}".format(cve))
        return "\n".join(lines)

    @property
    def release_packages(self) -> "Dict[str, Dict[str, Dict[str, str]]]":
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
        series = util.get_platform_info()["series"]
        self._release_packages = {}  # type: Dict[str, Dict[str, Any]]
        # Organize source and binary packages under a common source package key
        for pkg in self.response.get("release_packages", {}).get(series, []):
            if pkg.get("is_source"):
                # Create a "source" key under src_pkg_name with API response
                if pkg["name"] in self._release_packages:
                    if "source" in self._release_packages[pkg["name"]]:
                        raise exceptions.SecurityAPIMetadataError(
                            "{usn} metadata defines duplicate source packages"
                            " {pkg}".format(usn=self.id, pkg=pkg["name"]),
                            issue_id=self.id,
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
                        "{issue} metadata does not define release_packages"
                        " source_link for {bin_pkg}.".format(
                            issue=self.id, bin_pkg=pkg["name"]
                        ),
                        issue_id=self.id,
                    )
                elif "/" not in pkg["source_link"]:
                    raise exceptions.SecurityAPIMetadataError(
                        "{issue} metadata has unexpected release_packages"
                        " source_link value for {bin_pkg}: {link}".format(
                            issue=self.id,
                            bin_pkg=pkg["name"],
                            link=pkg["source_link"],
                        ),
                        issue_id=self.id,
                    )
                source_pkg_name = pkg["source_link"].split("/")[-1]
                if source_pkg_name not in self._release_packages:
                    self._release_packages[source_pkg_name] = {}
                self._release_packages[source_pkg_name][pkg["name"]] = pkg
        return self._release_packages


def query_installed_source_pkg_versions() -> "Dict[str, Dict[str, str]]":
    """Return a dict of all source packages installed on the system.

    The dict keys will be source package name: "krb5". The value will be a dict
    with keys binary_pkg and version.
    """
    series = util.get_platform_info()["series"]
    if series == "trusty":
        status_field = "${Status}"
    else:
        status_field = "${db:Status-Status}"
    out, _err = util.subp(
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


def merge_usn_released_binary_package_versions(
    usns: "List[USN]"
) -> "Dict[str,  Dict[str, Dict[str, str]]]":
    """Walk related USNs, merging the released binary package versions.

    For each USN, iterate over release_packages to collect released binary
        package names and required fix version. If multiple related USNs
        require differnt version fixes to the same binary package, track the
        maximum version required across all USNs.

    :return: Dict keyed by source package name. Under each source package will
        be a dict with binary package name as keys and binary package metadata
        as the value.
    """
    usn_pkg_versions = {}
    for usn in usns:
        # Aggregate USN.release_package binary versions into usn_pkg_versions
        for src_pkg, binary_pkg_versions in usn.release_packages.items():
            if src_pkg not in usn_pkg_versions:
                usn_pkg_versions[src_pkg] = binary_pkg_versions
            else:
                # Since src_pkg exists, only record this USN's binary version
                # when it is greater than the previous version in usn_src_pkg.
                usn_src_pkg = usn_pkg_versions[src_pkg]
                for binary_pkg, binary_pkg_md in binary_pkg_versions.items():
                    if binary_pkg not in usn_src_pkg:
                        usn_src_pkg[binary_pkg] = binary_pkg_md
                    else:
                        prev_version = usn_src_pkg[binary_pkg]["version"]
                        current_version = binary_pkg_md["version"]
                        if not version_cmp_le(current_version, prev_version):
                            # binary_version is greater than prev_version
                            usn_src_pkg[binary_pkg] = binary_pkg_md
    return usn_pkg_versions


def fix_security_issue_id(cfg: UAConfig, issue_id: str) -> None:
    issue_id = issue_id.upper()
    client = UASecurityClient(cfg=cfg)
    installed_packages = query_installed_source_pkg_versions()
    if "CVE" in issue_id:
        try:
            cve = client.get_cve(cve_id=issue_id)
            usns = client.get_notices(details=issue_id)
        except SecurityAPIError as e:
            msg = str(e)
            if "not found" in msg.lower():
                msg = status.MESSAGE_SECURITY_FIX_NOT_FOUND_ISSUE.format(
                    issue_id=issue_id
                )
            raise exceptions.UserFacingError(msg)
        affected_pkg_status = get_cve_affected_source_packages_status(
            cve=cve, installed_packages=installed_packages
        )
        print(cve.get_url_header())
        usn_released_pkgs = merge_usn_released_binary_package_versions(usns)
    else:  # USN
        related_usns = {}
        try:
            usn = client.get_notice(notice_id=issue_id)
            for cve_id in usn.cve_ids:
                for related_usn in client.get_notices(details=cve_id):
                    if related_usn.id not in related_usns:
                        related_usns[related_usn.id] = related_usn
            usns = list(sorted(related_usns.values(), key=lambda x: x.id))
        except SecurityAPIError as e:
            msg = str(e)
            if "not found" in msg.lower():
                msg = status.MESSAGE_SECURITY_FIX_NOT_FOUND_ISSUE.format(
                    issue_id=issue_id
                )
            raise exceptions.UserFacingError(msg)
        affected_pkg_status = get_usn_affected_packages_status(
            usn=usn, installed_packages=installed_packages
        )
        usn_released_pkgs = merge_usn_released_binary_package_versions(usns)
        print(usn.get_url_header())
        related_cves = set(itertools.chain(*[u.cve_ids for u in usns]))
        if not related_cves:
            raise exceptions.SecurityAPIMetadataError(
                "{} metadata defines no related CVEs.".format(issue_id),
                issue_id=issue_id,
            )
        if not usn.response["release_packages"]:
            # Since usn.release_packages filters to our current release only
            # check overall metadata and error if empty.
            raise exceptions.SecurityAPIMetadataError(
                "{} metadata defines no fixed package versions.".format(
                    issue_id
                ),
                issue_id=issue_id,
            )
    prompt_for_affected_packages(
        cfg=cfg,
        issue_id=issue_id,
        affected_pkg_status=affected_pkg_status,
        installed_packages=installed_packages,
        usn_released_pkgs=usn_released_pkgs,
    )


def get_usn_affected_packages_status(
    usn: USN, installed_packages: "Dict[str, Dict[str, str]]"
) -> "Dict[str, CVEPackageStatus]":
    """Walk CVEs related to a USN and return a dict of all affected packages.

    :return: Dict keyed on source package name, with active CVEPackageStatus
        for the current Ubuntu release.
    """
    affected_pkgs = {}  # type: Dict[str, CVEPackageStatus]
    for cve in usn.get_cves_metadata():
        for pkg_name, pkg_status in get_cve_affected_source_packages_status(
            cve, installed_packages
        ).items():
            if pkg_name not in affected_pkgs:
                affected_pkgs[pkg_name] = pkg_status
            else:
                current_ver = affected_pkgs[pkg_name].fixed_version
                if not version_cmp_le(current_ver, pkg_status.fixed_version):
                    affected_pkgs[pkg_name] = pkg_status
    return affected_pkgs


def get_cve_affected_source_packages_status(
    cve: CVE, installed_packages: "Dict[str, Dict[str, str]]"
) -> "Dict[str, CVEPackageStatus]":
    """Get a dict of any CVEPackageStatuses affecting this Ubuntu release.

    :return: Dict of active CVEPackageStatus keyed by source package names.
    """
    affected_pkg_versions = {}
    for source_pkg, package_status in cve.packages_status.items():
        if source_pkg in installed_packages:
            affected_pkg_versions[source_pkg] = package_status
    return affected_pkg_versions


def print_affected_packages_header(
    issue_id: str, affected_pkg_status: "Dict[str, CVEPackageStatus]"
):
    """Print header strings describing affected packages related to a CVE/USN.

    :param issue_id: String of USN or CVE issue id.
    :param affected_pkg_status: Dict keyed on source package name, with active
        CVEPackageStatus for the current Ubuntu release.
    """
    count = len(affected_pkg_status)
    if count == 0:
        print(
            status.MESSAGE_SECURITY_AFFECTED_PKGS.format(
                count="No", plural_str="s are"
            )
            + "."
        )
        print(status.MESSAGE_SECURITY_ISSUE_UNAFFECTED.format(issue=issue_id))
        return

    if count == 1:
        plural_str = " is"
    else:
        plural_str = "s are"
    msg = status.MESSAGE_SECURITY_AFFECTED_PKGS.format(
        count=count, plural_str=plural_str
    )
    print(msg + ": " + ", ".join(sorted(affected_pkg_status.keys())))


def override_usn_release_package_status(
    pkg_status: CVEPackageStatus,
    usn_src_released_pkgs: "Dict[str, Dict[str, str]]",
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
    status_groups = {}
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


def prompt_for_affected_packages(
    cfg: UAConfig,
    issue_id: str,
    affected_pkg_status: "Dict[str, CVEPackageStatus]",
    installed_packages: "Dict[str, Dict[str, str]]",
    usn_released_pkgs: "Dict[str, Dict[str, Dict[str, str]]]",
) -> None:
    """Process security CVE dict returning a CVEStatus object.

    Since CVEs point to a USN if active, get_notice may be called to fill in
    CVE title details.
    """
    count = len(affected_pkg_status)
    print_affected_packages_header(issue_id, affected_pkg_status)
    if count == 0:
        return
    upgrade_packages = []  # Packages from Ubuntu standard updates
    upgrade_packages_ua = []  # Packages requiring UA subscription
    fix_message = status.MESSAGE_SECURITY_ISSUE_RESOLVED.format(issue=issue_id)
    pkg_index = 0

    pkg_status_groups = group_by_usn_package_status(
        affected_pkg_status, usn_released_pkgs
    )
    for status_value, pkg_status_group in sorted(pkg_status_groups.items()):
        if status_value != "released":
            fix_message = status.MESSAGE_SECURITY_ISSUE_NOT_RESOLVED.format(
                issue=issue_id
            )
            msg_index = []
            src_pkgs = []
            for src_pkg, pkg_status in pkg_status_group:
                pkg_index += 1
                msg_index.append("{}/{}".format(pkg_index, count))
                src_pkgs.append(src_pkg)

            print(
                "{} {}:\n{}".format(
                    "(" + ", ".join(msg_index) + ")",
                    ", ".join(sorted(src_pkgs)),
                    pkg_status.status_message,
                )
            )
        else:
            for src_pkg, pkg_status in pkg_status_group:
                pkg_index += 1
                print("({}/{}) {}:".format(pkg_index, count, src_pkg))
                print(pkg_status.status_message)
                update_needed = False
                for binary_pkg, version in installed_packages[src_pkg].items():
                    usn_released_src = usn_released_pkgs.get(src_pkg, {})
                    if binary_pkg not in usn_released_src:
                        msg = (
                            "{issue} metadata defines no fixed version for"
                            " {pkg}.".format(pkg=binary_pkg, issue=issue_id)
                        )
                        raise exceptions.SecurityAPIMetadataError(
                            msg, issue_id
                        )
                    fixed_pkg = usn_released_src[binary_pkg]
                    fixed_version = fixed_pkg["version"]  # type: ignore
                    if not version_cmp_le(fixed_version, version):
                        update_needed = True
                        if pkg_status.requires_ua:
                            upgrade_packages_ua.append(binary_pkg)
                        else:
                            upgrade_packages.append(binary_pkg)
                if update_needed:
                    print(status.MESSAGE_SECURITY_UPDATE_NOT_INSTALLED)
                else:
                    print(status.MESSAGE_SECURITY_UPDATE_INSTALLED)
    if not any([upgrade_packages, upgrade_packages_ua]):
        print(fix_message)
    elif upgrade_packages_and_attach(
        cfg, upgrade_packages, upgrade_packages_ua
    ):
        print(fix_message)


def _prompt_for_attach(cfg: UAConfig) -> bool:
    """Prompt for attach to a subscription or token.

    :return: True if attach performed.
    """
    import argparse
    from uaclient import cli

    cloud_type = get_cloud_type()
    if cloud_type in PRO_CLOUDS:
        print(
            status.MESSAGE_SECURITY_USE_PRO_TMPL.format(
                title=CLOUD_TYPE_TO_TITLE.get(cloud_type), cloud=cloud_type
            )
        )
    print(status.MESSAGE_SECURITY_UPDATE_NOT_INSTALLED_SUBSCRIPTION)
    choice = util.prompt_choices(
        "Choose: [S]ubscribe at ubuntu.com [A]ttach existing token [C]ancel",
        valid_choices=["s", "a", "c"],
    )
    if choice == "c":
        return False
    if choice == "s":
        print(status.PROMPT_UA_SUBSCRIPTION_URL)
        # TODO(GH: #1413: magic subscription attach)
        input("Hit [Enter] when subscription is complete.")
    if choice in ("a", "s"):
        print(status.PROMPT_ENTER_TOKEN)
        token = input("> ")
        print(status.colorize_commands([["ua", "attach", token]]))
        return bool(
            0
            == cli.action_attach(
                argparse.Namespace(token=token, auto_enable=True), cfg
            )
        )
    return True


def upgrade_packages_and_attach(
    cfg: UAConfig,
    upgrade_packages: "List[str]",
    upgrade_packages_ua: "List[str]",
) -> bool:
    """Upgrade available packages to fix a CVE.

    Upgrade all packages in Ubuntu standard updates regardless of attach
    status.

    For UA upgrades, prompt regarding system attach prior to upgrading UA
    packages.

    :return: True if package upgrade completed or unneeded, False otherwise.
    """
    if not any([upgrade_packages, upgrade_packages_ua]):
        return True
    if os.getuid() != 0:
        print(status.MESSAGE_SECURITY_APT_NON_ROOT)
        return False
    if upgrade_packages_ua:
        if not cfg.is_attached:
            if not _prompt_for_attach(cfg):
                return False  # User opted to cancel
    packages = sorted(upgrade_packages + upgrade_packages_ua)
    print(
        status.colorize_commands(
            [
                ["apt", "update", "&&"]
                + ["apt", "install", "--only-upgrade", "-y"]
                + packages
            ]
        )
    )
    apt.run_apt_command(
        cmd=["apt-get", "update"], error_msg=status.MESSAGE_APT_UPDATE_FAILED
    )
    apt.run_apt_command(
        cmd=["apt-get", "install", "--only-upgrade", "-y"] + packages,
        error_msg=status.MESSAGE_APT_INSTALL_FAILED,
        env={"DEBIAN_FRONTEND": "noninteractive"},
    )
    return True


def version_cmp_le(version1: str, version2: str) -> bool:
    """Return True when version1 is less than or equal to version2."""
    try:
        util.subp(["dpkg", "--compare-versions", version1, "le", version2])
        return True
    except util.ProcessExecutionError:
        return False
