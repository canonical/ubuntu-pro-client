import os
import socket

from uaclient.config import UAConfig
from uaclient import exceptions
from uaclient import status
from uaclient import serviceclient
from uaclient import util
from uaclient import apt

CVE_OR_USN_REGEX = (
    r"((CVE|cve)-\d{4}-\d{4,7}$|(USN|usn|LSN|lsn)-\d{1,5}-\d{1,2}$)"
)

try:
    from typing import Any, Dict, List, Optional  # noqa: F401
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass


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

        @return: List of USN instances based on the the JSON response.
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
        return [USN(client=self, response=usn_md) for usn_md in usns_response]

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
            self._notices.append(self.client.get_notice(notice_id=notice_id))
        return self._notices

    def get_url_header(self):
        """Return a string representing the URL for this cve."""
        title = self.description
        for notice in self.get_notices_metadata():
            # Only look at the most recent USN title
            title = notice.title
            break
        return status.MESSAGE_SECURITY_URL.format(
            issue=self.id, title=title, url_path="{}".format(self.id)
        )

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

    def get_cves_metadata(self):
        if hasattr(self, "_cves"):
            return self._cves
        self._cves = []
        for cve_id in sorted(self.cve_ids, reverse=True):
            self._cves.append(self.client.get_cve(cve_id=cve_id))
        return self._cves

    def get_url_header(self):
        """Return a string representing the URL for this notice."""
        return status.MESSAGE_SECURITY_URL.format(
            issue=self.id,
            title=self.title,
            url_path="notices/{}".format(self.id),
        )


def query_installed_source_pkg_versions() -> "Dict[str, str]":
    """Return a dict of all source packages installed on the system.

    The dict keys will be source package name: "krb5". The value will be the
    package version.
    """
    out, _err = util.subp(
        [
            "dpkg-query",
            "-f=${Package},${Source},${Version},${db:Status-Status}\n",
            "-W",
        ]
    )
    installed_packages = {}  # type: Dict[str, str]
    for pkg_line in out.splitlines():
        pkg_name, source_pkg_name, pkg_version, status = pkg_line.split(",")
        if not source_pkg_name:
            # some package don't define the Source
            source_pkg_name = pkg_name
        if status != "installed":
            continue
        installed_packages[source_pkg_name] = pkg_version
    return installed_packages


def fix_security_issue_id(cfg: UAConfig, issue_id: str) -> None:
    issue_id = issue_id.upper()
    client = UASecurityClient(cfg=cfg)
    installed_packages = query_installed_source_pkg_versions()
    if "CVE" in issue_id:
        try:
            cve = client.get_cve(cve_id=issue_id)
        except SecurityAPIError as e:
            raise exceptions.UserFacingError(str(e))
        affected_pkg_status = get_cve_affected_packages_status(
            cve=cve, installed_packages=installed_packages
        )
        print(cve.get_url_header())
    else:  # USN
        try:
            usn = client.get_notice(notice_id=issue_id)
        except SecurityAPIError as e:
            raise exceptions.UserFacingError(str(e))
        affected_pkg_status = get_usn_affected_packages_status(
            usn=usn, installed_packages=installed_packages
        )
        print(usn.get_url_header())
    prompt_for_affected_packages(
        cfg=cfg,
        issue_id=issue_id,
        affected_pkg_status=affected_pkg_status,
        installed_packages=installed_packages,
    )


def get_usn_affected_packages_status(
    usn: USN, installed_packages: "Dict[str,str]"
) -> "Dict[str, CVEPackageStatus]":
    """Walk CVEs related to a USN and return a dict of all affected packages.

    :return: Dict keyed on source package name, with active CVEPackageStatus
        for the current Ubuntu release.
    """
    affected_pkgs = {}  # type: Dict[str, CVEPackageStatus]
    for cve in usn.get_cves_metadata():
        for pkg_name, pkg_status in get_cve_affected_packages_status(
            cve, installed_packages
        ).items():
            if pkg_name not in affected_pkgs:
                affected_pkgs[pkg_name] = pkg_status
            else:
                current_ver = affected_pkgs[pkg_name].fixed_version
                if not version_cmp_le(current_ver, pkg_status.fixed_version):
                    affected_pkgs[pkg_name] = pkg_status
    return affected_pkgs


def get_cve_affected_packages_status(
    cve: CVE, installed_packages: "Dict[str,str]"
) -> "Dict[str, CVEPackageStatus]":
    """Get a dict of any CVEPackageStatuses affecting this Ubuntu release.

    Filter any CVEPackageStatus that is "not-affected".

    :return: Dict of active CVEPackageStatus keyed by source package names.
    """
    affected_pkg_versions = {}
    for source_pkg, package_status in cve.packages_status.items():
        if source_pkg in installed_packages:
            if package_status.status != "not-affected":
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


def prompt_for_affected_packages(
    cfg: UAConfig,
    issue_id: str,
    affected_pkg_status: "Dict[str, CVEPackageStatus]",
    installed_packages: "Dict[str, str]",
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
    for pkg_num, pkg_name in enumerate(sorted(affected_pkg_status.keys()), 1):
        print("({}/{}) {}:".format(pkg_num, count, pkg_name))
        pkg_status = affected_pkg_status[pkg_name]
        print(pkg_status.status_message)
        if pkg_status.status == "released":
            fix_installed = version_cmp_le(
                pkg_status.fixed_version, installed_packages[pkg_name]
            )
            if fix_installed:
                print(status.MESSAGE_SECURITY_UPDATE_INSTALLED)
                print(
                    status.MESSAGE_SECURITY_ISSUE_RESOLVED.format(
                        issue=issue_id
                    )
                )
            else:
                print(status.MESSAGE_SECURITY_UPDATE_NOT_INSTALLED)
                if pkg_status.requires_ua:
                    upgrade_packages_ua.append(pkg_name)
                else:
                    upgrade_packages.append(pkg_name)
    upgrade_packages_and_attach(cfg, upgrade_packages, upgrade_packages_ua)


def upgrade_packages_and_attach(
    cfg: UAConfig,
    upgrade_packages: "List[str]",
    upgrade_packages_ua: "List[str]",
):
    """Upgrade available packages to fix a CVE.

    Upgrade all packages in Ubuntu standard updates regardless of attach
    status.

    For UA upgrades, prompt regarding system attach prior to upgrading UA
    packages.
    """
    if upgrade_packages:
        if os.getuid() != 0:
            print(status.MESSAGE_SECURITY_APT_NON_ROOT)
            return

        apt.run_apt_command(
            cmd=["apt-get", "update"],
            error_msg=status.MESSAGE_APT_UPDATE_FAILED,
            print_cmd=True,
        )

        apt.run_apt_command(
            cmd=["apt-get", "install", "--only-upgrade", "-y"]
            + upgrade_packages,
            error_msg=status.MESSAGE_APT_INSTALL_FAILED,
            env={"DEBIAN_FRONTEND": "noninteractive"},
            print_cmd=True,
        )
    if upgrade_packages_ua:
        if cfg.is_attached:
            print(
                "TODO: GH: #1402: apt commands to install missing UA updates"
            )
        else:
            print(status.MESSAGE_SECURITY_UPDATE_NOT_INSTALLED_SUBSCRIPTION)
            choice = util.prompt_choices(
                "Choose: [S]ubscribe at ubuntu.com [A]ttach"
                " existing token [C]ancel",
                valid_choices=["s", "a", "c"],
            )
            print("TODO react to subscription choice:{} GH: #".format(choice))


def version_cmp_le(version1, version2) -> bool:
    """Return True when version1 is less than or equal to version2."""
    try:
        util.subp(["dpkg", "--compare-versions", version1, "le", version2])
        return True
    except util.ProcessExecutionError:
        return False
