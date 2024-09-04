import abc
import enum
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from uaclient import apt, exceptions, http, system, util
from uaclient.api.u.pro.security.fix._common import (
    query_installed_source_pkg_versions,
)
from uaclient.api.u.pro.status.enabled_services.v1 import _enabled_services
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue
from uaclient.defaults import (
    VULNERABILITY_CACHE_PATH,
    VULNERABILITY_DATA_CACHE,
    VULNERABILITY_DATA_TMPL,
    VULNERABILITY_PUBLISH_DATE_CACHE,
)
from uaclient.entitlements.fips import FIPSEntitlement, FIPSUpdatesEntitlement
from uaclient.files.data_types import DataObjectFile
from uaclient.files.files import UAFile


class VulnerabilityCacheDate(DataObject):
    fields = [Field("cache_date", StringDataValue)]

    def __init__(self, cache_date):
        self.cache_date = cache_date


@enum.unique
class VulnerabilityStatus(enum.Enum):
    """
    An enum to represent the status of a vulnerability
    """

    NO_FIX_AVAILABLE = "no"
    PARTIAL_FIX_AVAILABLE = "partial"
    FULL_FIX_AVAILABLE = "yes"


class VulnerabilityData:

    def __init__(
        self,
        cfg: UAConfig,
        data_file: Optional[str] = None,
        series: Optional[str] = None,
    ):
        self.cfg = cfg
        self.data_file = data_file
        self.series = series

    def _get_cache_data_path(self, series: str):
        return os.path.join(
            VULNERABILITY_CACHE_PATH, series, VULNERABILITY_DATA_CACHE
        )

    def _get_cache_published_date_path(self, series: str):
        return os.path.join(
            VULNERABILITY_CACHE_PATH, series, VULNERABILITY_PUBLISH_DATE_CACHE
        )

    def _save_cache_data(self, series: str, json_data: Dict[str, Any]):
        system.write_file(
            self._get_cache_data_path(series), json.dumps(json_data)
        )

    def _save_cache_publish_date(
        self, cache_date_file: DataObjectFile, published_date: str
    ):
        cache_date_file.write(
            VulnerabilityCacheDate(cache_date=published_date)
        )

    def _parse_published_date(self, published_date: str):
        format_str = "%a, %d %b %Y %H:%M:%S %Z"
        return datetime.strptime(published_date, format_str)

    def _get_published_date(self, data_url):
        resp = http.readurl(url=data_url, method="HEAD")
        return resp.headers["last-modified"]

    def _is_cache_valid(
        self,
        series: str,
        last_published_date: str,
        cache_date_file: DataObjectFile,
    ) -> bool:
        last_published_datetime = self._parse_published_date(
            last_published_date
        )

        cache_date_obj = cache_date_file.read()
        if not cache_date_obj:
            return False

        cache_published_datetime = self._parse_published_date(
            cache_date_obj.cache_date
        )

        return cache_published_datetime >= last_published_datetime

    def _get_cache_data(self, series: str):
        return json.loads(system.load_file(self._get_cache_data_path(series)))

    def _get_data_url(self, series):
        data_name = series

        enabled_services_names = [
            s.name for s in _enabled_services(self.cfg).enabled_services
        ]
        if FIPSEntitlement.name in enabled_services_names:
            data_name = "fips_{}".format(series)
        elif FIPSUpdatesEntitlement.name in enabled_services_names:
            data_name = "fips-updates_{}".format(series)

        data_file = VULNERABILITY_DATA_TMPL.format(series=data_name)
        return urljoin(self.cfg.vulnerability_data_url_prefix, data_file)

    def get(self):
        if self.data_file:
            return json.loads(system.load_file(self.data_file))

        series = self.series or system.get_release_info().series
        data_url = self._get_data_url(series)

        last_published_date = self._get_published_date(data_url)

        cache_date_file = DataObjectFile(
            data_object_cls=VulnerabilityCacheDate,
            ua_file=UAFile(
                name=VULNERABILITY_PUBLISH_DATE_CACHE,
                directory=os.path.join(VULNERABILITY_CACHE_PATH, series),
            ),
        )

        if self._is_cache_valid(series, last_published_date, cache_date_file):
            return self._get_cache_data(series)

        json_data = json.loads(
            http.download_xz_file_from_url(data_url).decode("utf-8")
        )

        if util.we_are_currently_root():
            self._save_cache_data(series, json_data)
            self._save_cache_publish_date(cache_date_file, last_published_date)

        return json_data


def _get_source_package_from_vulnerabilities_data(
    vulnerabilities_data: Dict[str, Any], bin_pkg_name: str
) -> str:
    for pkg_name, pkg_info in vulnerabilities_data.get("packages", {}).items():
        for _, source_info in pkg_info.get("source_versions", {}).items():
            if bin_pkg_name in source_info["binary_packages"].keys():
                return pkg_name

    return ""


class ProManifestSourcePackage:
    name = "Pro manifest"

    # This pkg part of this regex was created accordingly to the debian
    # name pattern defined here:
    # https://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-source
    PKG_RE = re.compile(r"^(?P<pkg>[\w\-\.\+]+)(:\w+)?\s+(?P<version>.+)$")

    @staticmethod
    def parse(manifest_file: str) -> Dict[str, str]:
        pkgs = {}

        with open(manifest_file, "r") as f:
            for line in f.readlines():
                re_match = ProManifestSourcePackage.PKG_RE.match(line)
                if re_match:
                    match_groups = re_match.groupdict()
                    pkg = match_groups["pkg"]

                    if pkg == "snap":
                        continue

                    pkgs[pkg] = match_groups["version"]
                else:
                    raise exceptions.ManifestParseError(
                        name=ProManifestSourcePackage.name, error_line=line
                    )

        return pkgs


class SourcePackages:
    SUPPORTED_MANIFESTS = [ProManifestSourcePackage]

    def __init__(
        self,
        vulnerabilities_data: Dict[str, Any],
        manifest_file: Optional[str] = None,
    ):
        self.manifest_file = manifest_file
        self.vulnerabilities_data = vulnerabilities_data

    def get(self):
        if not self.manifest_file:
            return query_installed_source_pkg_versions()
        else:
            return self.parse_manifest_file()

    def parse_manifest_file(self) -> Dict[str, Dict[str, str]]:
        if not self.manifest_file:
            return {}

        manifest_pkgs = None

        for manifest_parser_cls in self.SUPPORTED_MANIFESTS:
            try:
                manifest_pkgs = manifest_parser_cls.parse(self.manifest_file)
                break
            except exceptions.ManifestParseError:
                continue

        if not manifest_pkgs:
            raise exceptions.UnsupportedManifestFile

        source_pkgs = {}  # type: Dict[str, Dict[str, str]]
        for pkg, version in manifest_pkgs.items():
            source_pkg = _get_source_package_from_vulnerabilities_data(
                self.vulnerabilities_data, pkg
            )
            if source_pkg in source_pkgs:
                source_pkgs[source_pkg][pkg] = version
            else:
                source_pkgs[source_pkg] = {pkg: version}

        return source_pkgs


def _get_vulnerability_fix_status(
    affected_packages: List[Dict[str, Optional[str]]],
) -> VulnerabilityStatus:
    vulnerability_status = VulnerabilityStatus.NO_FIX_AVAILABLE
    num_fixes = 0
    for pkg in affected_packages:
        if pkg.get("fix_version") is not None:
            num_fixes += 1

    if num_fixes == len(affected_packages):
        vulnerability_status = VulnerabilityStatus.FULL_FIX_AVAILABLE
    elif num_fixes != 0:
        vulnerability_status = VulnerabilityStatus.PARTIAL_FIX_AVAILABLE

    return vulnerability_status


class VulnerabilityParser(metaclass=abc.ABCMeta):
    vulnerability_type = None  # type: str

    @abc.abstractmethod
    def get_package_vulnerabilities(self, affected_pkg: Dict[str, Any]):
        pass

    @abc.abstractmethod
    def _post_process_vulnerability_info(
        self,
        installed_pkgs_by_source: Dict[str, Dict[str, str]],
        vulnerability_info: Dict[str, Any],
        vulnerabilities_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        pass

    def _add_new_vulnerability(
        self,
        affected_vulns: Dict[str, Any],
        vuln_name: str,
        vuln_info: Dict[str, Any],
    ):
        affected_vulns[vuln_name] = vuln_info
        affected_vulns[vuln_name]["affected_packages"] = []

    def _add_unfixable_vulnerability(
        self,
        affected_vulns: Dict[str, Any],
        bin_installed_pkg_name: str,
        bin_installed_version: str,
        vuln_name: str,
        vuln_info: Dict[str, Any],
        vuln_pkg_status: str,
    ):
        if vuln_name not in affected_vulns:
            self._add_new_vulnerability(
                affected_vulns=affected_vulns,
                vuln_name=vuln_name,
                vuln_info=vuln_info,
            )

        affected_vulns[vuln_name]["affected_packages"].append(
            {
                "name": bin_installed_pkg_name,
                "current_version": bin_installed_version,
                "fix_version": None,
                "status": vuln_pkg_status,
                "fix_available_from": None,
            }
        )

    def _add_fixable_vulnerability(
        self,
        affected_vulns: Dict[str, Any],
        bin_installed_pkg_name: str,
        bin_installed_version: str,
        vuln_bin_fix_version: str,
        fix_pocket: str,
        vuln_name: str,
        vuln_pkg_status: str,
        vuln_info: Dict[str, Any],
    ):
        if vuln_name not in affected_vulns:
            self._add_new_vulnerability(
                affected_vulns=affected_vulns,
                vuln_name=vuln_name,
                vuln_info=vuln_info,
            )

        affected_vulns[vuln_name]["affected_packages"].append(
            {
                "name": bin_installed_pkg_name,
                "current_version": bin_installed_version,
                "fix_version": vuln_bin_fix_version,
                "status": vuln_pkg_status,
                "fix_available_from": fix_pocket,
            }
        )

    def is_vulnerability_not_fixable(
        self,
        vuln_source_fixed_version: str,
        vuln_pkg_status: str,
    ):
        # if the vulnerability fixed version is None,
        # that means that no fix has been published
        # yet.
        if vuln_source_fixed_version is None:
            if vuln_pkg_status != "not-vulnerable":
                return True

        return False

    def _get_installed_source_pkg_version(self, binary_pkg_name: str):
        out, _ = system.subp(
            [
                "dpkg-query",
                "-W",
                "-f=${source:Version}",
                binary_pkg_name,
            ]
        )

        return out

    def is_vulnerability_valid_but_not_fixable(
        self,
        vuln_bin_fix_version: Optional[str],
        bin_installed_pkg_name: str,
        vuln_source_fixed_version: str,
    ):
        """
        This method checks if we detect that a vulnerability
        affects a binary package but can't be fixed. This
        situation can happen during a package transition.

        For example, suppose we have this entry for pkg1:

        "pkg1": {
          "source_version": {
            "1.0": {
              "bin-pkg1": "1.0",
              "bin-pkg2": "1.1",
            },
            "1.1": {
              "bin-pkg1": "1.2"
            }
          }
        }

        Notice that version 1.1 doesn't produce bin-pkg2 anymore.
        Therefore, if we detect that a vulnerability is fixable
        by version 1.1, we won't find the binary fixable bersion for
        the bin-pkg2 package.

        If we detect that, we will:

        1. Check if version of the source package associated with the
           binary package is higher thatn the vulnerability source fix
           version. If it is, we can say that the system is not vulnerable.
        2. If it is not, then the binary package is affected by the issue, but
           we can't say what the user needs to do to fix it.
        """

        if vuln_bin_fix_version is None:
            installed_source_pkg_version = (
                self._get_installed_source_pkg_version(bin_installed_pkg_name)
            )

            if (
                apt.version_compare(
                    installed_source_pkg_version, vuln_source_fixed_version
                )
                > 0
            ):
                return False
            else:
                return True

        return False

    def vulnerability_affects_system(
        self,
        bin_installed_version: str,
        vuln_bin_fix_version: str,
    ):
        return (
            apt.version_compare(vuln_bin_fix_version, bin_installed_version)
            > 0
        )

    def _list_binary_packages(self, installed_pkgs_by_source: Dict[str, Any]):
        for source_pkg, binary_pkgs in installed_pkgs_by_source.items():
            for (
                binary_pkg_name,
                binary_installed_version,
            ) in sorted(binary_pkgs.items()):
                yield source_pkg, binary_pkg_name, binary_installed_version

    def get_vulnerabilities_for_installed_pkgs(
        self,
        vulnerabilities_data: Dict[str, Any],
        installed_pkgs_by_source: Dict[str, Dict[str, str]],
    ):
        vulnerabilities = {}  # type: Dict[str, Any]

        affected_pkgs = vulnerabilities_data.get("packages", {})
        vulns_info = vulnerabilities_data.get("security_issues", {}).get(
            self.vulnerability_type, {}
        )

        for (
            source_pkg,
            bin_installed_pkg_name,
            bin_installed_version,
        ) in self._list_binary_packages(installed_pkgs_by_source):
            affected_pkg = affected_pkgs.get(source_pkg, {})
            vuln_source_versions = affected_pkg.get("source_versions", {})

            for vuln_name, vuln in self.get_package_vulnerabilities(
                affected_pkg
            ).items():
                vuln_info = vulns_info.get(vuln_name, "")
                vuln_source_fixed_version = vuln.get("source_fixed_version")
                vuln_pkg_status = vuln.get("status")

                if self.is_vulnerability_not_fixable(
                    vuln_pkg_status=vuln_pkg_status,
                    vuln_source_fixed_version=vuln_source_fixed_version,
                ):
                    if vuln_name not in vulnerabilities:
                        vuln_info = self._post_process_vulnerability_info(
                            installed_pkgs_by_source,
                            vuln_info,
                            vulnerabilities_data,
                        )

                    self._add_unfixable_vulnerability(
                        affected_vulns=vulnerabilities,
                        bin_installed_pkg_name=bin_installed_pkg_name,
                        bin_installed_version=bin_installed_version,
                        vuln_name=vuln_name,
                        vuln_info=vuln_info,
                        vuln_pkg_status=vuln_pkg_status,
                    )
                    continue

                try:
                    pocket = vuln_source_versions[
                        vuln_source_fixed_version
                    ].get("pocket")
                    vuln_bin_fix_version = (
                        vuln_source_versions[vuln_source_fixed_version]
                        .get("binary_packages", {})
                        .get(bin_installed_pkg_name)
                    )
                except KeyError:
                    # There is bug in the data where some sources are
                    # not present. The Security team is already aware
                    # of this issue and they are handling it
                    continue

                if self.is_vulnerability_valid_but_not_fixable(
                    vuln_bin_fix_version,
                    bin_installed_pkg_name,
                    vuln_source_fixed_version,
                ):
                    if vuln_name not in vulnerabilities:
                        vuln_info = self._post_process_vulnerability_info(
                            installed_pkgs_by_source,
                            vuln_info,
                            vulnerabilities_data,
                        )

                    self._add_unfixable_vulnerability(
                        affected_vulns=vulnerabilities,
                        bin_installed_pkg_name=bin_installed_pkg_name,
                        bin_installed_version=bin_installed_version,
                        vuln_name=vuln_name,
                        vuln_info=vuln_info,
                        vuln_pkg_status="unknown",
                    )
                    continue

                if vuln_bin_fix_version is None:
                    continue

                if self.vulnerability_affects_system(
                    bin_installed_version,
                    vuln_bin_fix_version,
                ):
                    if vuln_name not in vulnerabilities:
                        vuln_info = self._post_process_vulnerability_info(
                            installed_pkgs_by_source,
                            vuln_info,
                            vulnerabilities_data,
                        )

                    self._add_fixable_vulnerability(
                        affected_vulns=vulnerabilities,
                        bin_installed_pkg_name=bin_installed_pkg_name,
                        bin_installed_version=bin_installed_version,
                        vuln_bin_fix_version=vuln_bin_fix_version,
                        fix_pocket=pocket,
                        vuln_name=vuln_name,
                        vuln_info=vuln_info,
                        vuln_pkg_status=vuln_pkg_status,
                    )

        return vulnerabilities
