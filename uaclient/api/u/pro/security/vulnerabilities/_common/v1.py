import abc
import datetime
import enum
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple
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
        self.series = series or system.get_release_info().series

    def _get_cache_data_path(self):
        return os.path.join(
            VULNERABILITY_CACHE_PATH, self.series, VULNERABILITY_DATA_CACHE
        )

    def _get_cache_published_date_path(self):
        return os.path.join(
            VULNERABILITY_CACHE_PATH,
            self.series,
            VULNERABILITY_PUBLISH_DATE_CACHE,
        )

    def _save_cache_data(self, json_data: Dict[str, Any]):
        system.write_file(self._get_cache_data_path(), json.dumps(json_data))

    def _save_cache_publish_date(
        self, cache_date_file: DataObjectFile, published_date: str
    ):
        cache_date_file.write(
            VulnerabilityCacheDate(cache_date=published_date)
        )

    def _parse_published_date(self, published_date: str):
        format_str = "%a, %d %b %Y %H:%M:%S %Z"
        return datetime.datetime.strptime(published_date, format_str)

    def _get_published_date(self):
        resp = http.readurl(url=self._get_data_url(), method="HEAD")
        return resp.headers["last-modified"]

    def is_cache_valid(self) -> Tuple[bool, Optional[datetime.datetime]]:
        last_published_date = self._get_published_date()
        cache_date_file = self._get_cache_file()

        return self._is_cache_valid(last_published_date, cache_date_file)

    def _is_cache_valid(
        self,
        last_published_date: str,
        cache_date_file: DataObjectFile,
    ) -> Tuple[bool, Optional[datetime.datetime]]:
        last_published_datetime = self._parse_published_date(
            last_published_date
        )

        cache_date_obj = cache_date_file.read()
        if not cache_date_obj:
            return (False, None)

        cache_published_datetime = self._parse_published_date(
            cache_date_obj.cache_date
        )

        return (
            cache_published_datetime >= last_published_datetime,
            last_published_datetime - cache_published_datetime,
        )

    def _get_cache_data(self):
        return json.loads(system.load_file(self._get_cache_data_path()))

    def _get_data_url(self):
        data_name = self.series

        enabled_services_names = [
            s.name for s in _enabled_services(self.cfg).enabled_services
        ]
        if FIPSEntitlement.name in enabled_services_names:
            data_name = "fips_{}".format(self.series)
        elif FIPSUpdatesEntitlement.name in enabled_services_names:
            data_name = "fips-updates_{}".format(self.series)

        data_file = VULNERABILITY_DATA_TMPL.format(series=data_name)
        return urljoin(self.cfg.vulnerability_data_url_prefix, data_file)

    def _get_cache_file(self):
        return DataObjectFile(
            data_object_cls=VulnerabilityCacheDate,
            ua_file=UAFile(
                name=VULNERABILITY_PUBLISH_DATE_CACHE,
                directory=os.path.join(VULNERABILITY_CACHE_PATH, self.series),
            ),
        )

    def get(self, fetch_data: bool = True):
        if self.data_file:
            return json.loads(system.load_file(self.data_file))

        last_published_date = self._get_published_date()
        cache_date_file = self._get_cache_file()

        cache_valid, _ = self._is_cache_valid(
            last_published_date, cache_date_file
        )

        if cache_valid:
            return self._get_cache_data()

        if fetch_data:
            json_data = json.loads(
                http.download_xz_file_from_url(self._get_data_url()).decode(
                    "utf-8"
                )
            )

            if util.we_are_currently_root():
                self._save_cache_data(json_data)
                self._save_cache_publish_date(
                    cache_date_file, last_published_date
                )

            return json_data

        return None


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

    def get_vulnerabilities_for_installed_pkgs(
        self,
        vulnerabilities_data: Dict[str, Any],
        installed_pkgs_by_source: Dict[str, Dict[str, str]],
    ):
        vulnerabilities = {}

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
                vuln_info = vulns_info.get(vuln_name, {})
                vuln_fixed_version = vuln.get("source_fixed_version")
                vuln_status = vuln.get("status")

                # if the vulnerability fixed version is None,
                # that means that no fix has been published
                # yet.
                if vuln_fixed_version is None:
                    if vuln_status != "not-vulnerable":
                        if vuln_name not in vulnerabilities:
                            vulnerabilities[vuln_name] = (
                                self._post_process_vulnerability_info(
                                    installed_pkgs_by_source,
                                    vuln_info,
                                    vulnerabilities_data,
                                )
                            )
                            vulnerabilities[vuln_name][
                                "affected_packages"
                            ] = []

                        vulnerabilities[vuln_name]["affected_packages"].extend(
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
                        if vuln_name not in vulnerabilities:
                            vulnerabilities[vuln_name] = (
                                self._post_process_vulnerability_info(
                                    installed_pkgs_by_source,
                                    vuln_info,
                                    vulnerabilities_data,
                                )
                            )
                            vulnerabilities[vuln_name][
                                "affected_packages"
                            ] = []

                        vulnerabilities[vuln_name]["affected_packages"].append(
                            {
                                "name": pkg_name,
                                "current_version": pkg_version,
                                "fix_version": fix_version,
                                "status": vuln_status,
                                "fix_available_from": pocket,
                            }
                        )

        return vulnerabilities
