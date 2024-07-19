import enum
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from uaclient import apt
from uaclient.api.exceptions import UnsupportedManifestFile
from uaclient.api.u.pro.security.fix._common import (
    query_installed_source_pkg_versions,
)
from uaclient.api.u.pro.status.enabled_services.v1 import _enabled_services
from uaclient.config import UAConfig
from uaclient.defaults import (
    VULNERABILITY_CACHE_PATH,
    VULNERABILITY_DATA_CACHE,
    VULNERABILITY_DATA_TMPL,
    VULNERABILITY_PUBLISH_DATE_CACHE,
)
from uaclient.entitlements.fips import FIPSEntitlement, FIPSUpdatesEntitlement
from uaclient.http import download_bz2_file_from_url, readurl
from uaclient.system import get_release_info, load_file, write_file
from uaclient.util import we_are_currently_root


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

    def _save_cache(
        self, series: str, json_data: Dict[str, Any], last_published_date
    ):
        write_file(self._get_cache_data_path(series), json.dumps(json_data))
        write_file(
            self._get_cache_published_date_path(series), last_published_date
        )

    def _parse_published_date(self, published_date: str):
        format_str = "%a, %d %b %Y %H:%M:%S GMT"
        return datetime.strptime(published_date, format_str)

    def _get_published_date(self, data_url):
        resp = readurl(url=data_url, method="HEAD")
        return resp.headers["last-modified"]

    def _is_cache_valid(self, series: str, last_published_date: str) -> bool:
        last_published_datetime = self._parse_published_date(
            last_published_date
        )

        try:
            cache_published_datetime = self._parse_published_date(
                load_file(self._get_cache_published_date_path(series))
            )
        except FileNotFoundError:
            return False

        return cache_published_datetime >= last_published_datetime

    def _get_cache_data(self, series: str):
        return json.loads(load_file(self._get_cache_data_path(series)))

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
            return json.loads(load_file(self.data_file))

        series = self.series or get_release_info().series
        data_url = self._get_data_url(series)

        last_published_date = self._get_published_date(data_url)

        if self._is_cache_valid(series, last_published_date):
            return self._get_cache_data(series)

        raw_json_data = download_bz2_file_from_url(data_url)

        json_data = json.loads(raw_json_data.decode("utf-8"))
        if we_are_currently_root():
            self._save_cache(series, json_data, last_published_date)

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
    PKG_RE = re.compile(r"^(?P<pkg>[\w\-\.\+]+)(:\w+)?\s+(?P<version>.+)$")

    @staticmethod
    def valid(manifest_file: str):
        with open(manifest_file, "r") as f:
            for line in f.readlines():
                if not ProManifestSourcePackage.PKG_RE.match(line):
                    return False

        return True

    @staticmethod
    def parse(manifest_file: str):
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
            if manifest_parser_cls.valid(self.manifest_file):
                manifest_pkgs = manifest_parser_cls.parse(self.manifest_file)
                break

        if not manifest_pkgs:
            raise UnsupportedManifestFile

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


class VulnerabilityParser:
    vulnerability_type = None  # type: str

    def __init__(
        self,
    ):
        self.vulnerabilities = {}

    def get_package_vulnerabilities(self, affected_pkg: Dict[str, Any]):
        raise NotImplementedError

    def parse_data(
        self,
        vulnerabilities_data: Dict[str, Any],
        installed_pkgs_by_source: Dict[str, Dict[str, str]],
    ):
        affected_pkgs = vulnerabilities_data.get("packages", {})
        vulns_info = vulnerabilities_data.get("security_issues", {}).get(
            self.vulnerability_type, {}
        )

        for source_pkg, binary_pkgs in installed_pkgs_by_source.items():
            affected_pkg = affected_pkgs.get(source_pkg, {})
            source_version = affected_pkg.get("source_versions", {})

            for vuln_name, vuln in self.get_package_vulnerabilities(
                affected_pkg
            ).items():
                vuln_info = vulns_info.get(vuln_name, "")
                vuln_fixed_version = vuln.get("source_fixed_version")
                vuln_status = vuln.get("status")

                # if the vulnerability fixed version is None,
                # that means that no fix has been published
                # yet.
                if vuln_fixed_version is None:
                    if vuln_status != "not-vulnerable":
                        if vuln_name not in self.vulnerabilities:
                            self.vulnerabilities[vuln_name] = vuln_info
                            self.vulnerabilities[vuln_name][
                                "affected_packages"
                            ] = []

                        self.vulnerabilities[vuln_name][
                            "affected_packages"
                        ].extend(
                            {
                                "name": pkg_name,
                                "current_version": pkg_version,
                                "fix_version": None,
                                "status": vuln_status,
                                "fix_available_from": None,
                            }
                            for pkg_name, pkg_version in sorted(
                                binary_pkgs.items()
                            )
                        )

                    continue

                for pkg_name, pkg_version in sorted(binary_pkgs.items()):
                    try:
                        pocket = source_version[vuln_fixed_version].get(
                            "pocket"
                        )
                        fix_version = (
                            source_version[vuln_fixed_version]
                            .get("binary_packages", {})
                            .get(pkg_name, "")
                        )
                    except KeyError:
                        # There is bug in the data where some sources are
                        # not present. The Security team is already aware
                        # of this issue and they are handling it
                        continue

                    if apt.version_compare(fix_version, pkg_version) > 0:
                        if vuln_name not in self.vulnerabilities:
                            self.vulnerabilities[vuln_name] = vuln_info
                            self.vulnerabilities[vuln_name][
                                "affected_packages"
                            ] = []

                        self.vulnerabilities[vuln_name][
                            "affected_packages"
                        ].append(
                            {
                                "name": pkg_name,
                                "current_version": pkg_version,
                                "fix_version": fix_version,
                                "status": vuln_status,
                                "fix_available_from": pocket,
                            }
                        )
