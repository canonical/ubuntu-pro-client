import bz2
import json
from typing import Any, Dict, Optional
from urllib.parse import urljoin

from uaclient import apt
from uaclient.config import UAConfig
from uaclient.http import download_file_from_url


@enum.unique
class VulnerabilityStatus(enum.Enum):
    """
    An enum to represent the status of a vulnerability
    """

    NO_FIX_AVAILABLE = "no"
    PARTIAL_FIX_AVAILABLE = "partial"
    FULL_FIX_AVAILABLE = "yes"


def fetch_vulnerabilities_data(cfg: UAConfig, series: str):
    data_file = "com.ubuntu.{}.pkg.json.bz2".format(series)
    data_url = urljoin(cfg.vulnerability_data_url_prefix, data_file)

    resp = download_file_from_url(url=data_url)

    decompressor = bz2.BZ2Decompressor()
    raw_json_data = decompressor.decompress(resp.body)  # type: ignore

    return json.loads(raw_json_data.decode("utf-8"))


def _get_source_package_from_vulnerabilities_data(
    vulnerabilities_data: Dict[str, Any], bin_pkg_name: str
) -> str:
    for pkg_name, pkg_info in vulnerabilities_data.get("packages", {}).items():
        for _, source_info in pkg_info.get("source_versions", {}).items():
            if bin_pkg_name in source_info["binary_packages"].keys():
                return pkg_name
            else:
                break

    return ""


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
                            self.vulnerabilities[vuln_name]["fixable"] = False
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
                    if (
                        apt.version_compare(vuln_fixed_version, pkg_version)
                        > 0
                    ):
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

                        if vuln_name not in self.vulnerabilities:
                            self.vulnerabilities[vuln_name] = vuln_info
                            self.vulnerabilities[vuln_name][
                                "affected_packages"
                            ] = []

                        self.vulnerabilities[vuln_name]["fixable"] = True
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
