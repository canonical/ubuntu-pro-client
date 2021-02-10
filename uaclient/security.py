from uaclient.config import UAConfig
from uaclient import exceptions
from uaclient import status
from uaclient import serviceclient
from uaclient import util

CVE_OR_USN_REGEX = r"(CVE-\d{4}-\d{4,7}|(USN|LSN)-\d{1,5}-\d{1,2})"

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

    cfg_url_base_attr = "security_url"
    api_error_cls = SecurityAPIError

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

    def __init__(self, cve_response: "Dict[str, str]"):
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
        elif self.status == "pending":
            return "A fix is coming soon. Try again tomorrow."
        elif self.status in ("ignored", "deferred"):
            return "Sorry, no fix is available."
        elif self.status == "released":
            return status.MESSAGE_SECURITY_FIX_RELEASE_STREAM.format(
                fix_stream=self.pocket_source
            )
        return "UNKNOWN: {}".format(self.status)

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
            # TODO(drop this once pockets are supplied from Security Team)
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

    def _get_related_notices(self):
        if hasattr(self, "notices"):
            return self.notices
        self.notices = {}
        for notice_id in self.response.get("notices", []):
            self.notices[notice_id] = self.client.get_notice(
                notice_id=notice_id
            )
        return self.notices

    @property
    def notice_ids(self):
        notices_md = self._get_related_notices()
        return list(notices_md.keys())

    @property
    def title(self):
        descr = self.response.get("description", "UNKNOWN_CVE_DESCRIPTION")
        notices = self._get_related_notices()
        if not notices:
            return descr
        # TODO(If multiple notices, which title to use?)
        for key in sorted(notices):
            return notices[key].title
        return descr

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

    def __init__(self, client: UASecurityClient, response: "Dict[str, str]"):
        self.response = response
        self.client = client

    @property
    def id(self):
        return self.response.get("id", "UNKNOWN_USN_ID").upper()

    @property
    def title(self):
        return self.response.get("title")


def query_installed_source_pkg_versions() -> "Dict[str, str]":
    """Return a dict of all source packages installed on the system.

    The dict keys will be source package name: "krb5". The value will be the
    package version.
    """
    out, _err = util.subp(
        ["dpkg-query", "-f=${Source},${Version},${db:Status-Status}\n", "-W"]
    )
    installed_packages = {}  # type: Dict[str, str]
    for pkg_line in out.splitlines():
        source_pkg_name, pkg_version, status = pkg_line.split(",")
        if status != "installed":
            continue
        installed_packages[source_pkg_name] = pkg_version
    return installed_packages


def fix_security_issue_id(cfg: UAConfig, issue_id: str) -> None:
    issue_id = issue_id.upper()
    client = UASecurityClient(cfg=cfg)
    installed_packages = query_installed_source_pkg_versions()
    if "CVE" in issue_id:
        affected_pkg_status = get_cve_affected_packages_status(
            client=client,
            issue_id=issue_id,
            installed_packages=installed_packages,
        )
    else:  # USN
        affected_pkg_status = get_usn_affected_packages_status(
            client=client, issue_id=issue_id
        )
    prompt_for_affected_packages(
        issue_id=issue_id,
        affected_pkg_status=affected_pkg_status,
        installed_packages=installed_packages,
    )


def get_usn_affected_packages_status(
    client: UASecurityClient, issue_id: str
) -> "Dict[str, CVEPackageStatus]":
    """Walk CVEs related to a USN and determine if all are fixed."""
    affected_pkg_versions = {}  # type: Dict[str, CVEPackageStatus]
    try:
        usn = client.get_notice(notice_id=issue_id)
    except SecurityAPIError as e:
        raise exceptions.UserFacingError(str(e))
    print(
        status.MESSAGE_SECURITY_URL.format(
            issue=usn.id,
            title=usn.title,
            url_path="notices/{}.json".format(usn.id.lower()),
        )
    )
    return affected_pkg_versions  # TODO(walk USN CVEs for affected packages)


def get_cve_affected_packages_status(
    client: UASecurityClient,
    issue_id: str,
    installed_packages: "Dict[str,str]",
) -> "Dict[str, CVEPackageStatus]":
    try:
        cve = client.get_cve(cve_id=issue_id)
    except SecurityAPIError as e:
        raise exceptions.UserFacingError(str(e))
    print(
        status.MESSAGE_SECURITY_URL.format(
            issue=cve.id,
            title=cve.title,
            url_path="{}.json".format(cve.id.lower()),
        )
    )
    affected_pkg_versions = {}
    for source_pkg, package_status in cve.packages_status.items():
        if source_pkg in installed_packages:
            if package_status.status != "not-affected":
                affected_pkg_versions[source_pkg] = package_status
    return affected_pkg_versions


def prompt_for_affected_packages(
    issue_id: str,
    affected_pkg_status: "Dict[str, CVEPackageStatus]",
    installed_packages: "Dict[str,str]",
) -> None:
    """Process security CVE dict returning a CVEStatus object.

    Since CVEs point to a USN if active, get_notice may be called to fill in
    CVE title details.
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
    msg_suffix = ": " + ", ".join(affected_pkg_status.keys())
    msgs = [msg + msg_suffix]
    for pkg_num, pkg_name in enumerate(affected_pkg_status.keys(), 1):
        msgs.append("({}/{}) {}:".format(pkg_num, count, pkg_name))
        pkg_status = affected_pkg_status[pkg_name]
        msgs.append(pkg_status.status_message)
        if pkg_status.status == "released":
            try:  # get_pkg_install_status_messages
                util.subp(
                    [
                        "dpkg",
                        "--compare-versions",
                        pkg_status.fixed_version,
                        "le",
                        installed_packages[pkg_name],
                    ]
                )
                fix_installed = True
            except util.ProcessExecutionError:
                fix_installed = False
            if fix_installed:
                msgs.append(status.MESSAGE_SECURITY_UPDATE_INSTALLED)
                msgs.append(
                    status.MESSAGE_SECURITY_ISSUE_RESOLVED.format(
                        issue=issue_id
                    )
                )
            else:
                msgs.append(status.MESSAGE_SECURITY_UPDATE_NOT_INSTALLED)
    for msg in msgs:
        print(msg)
