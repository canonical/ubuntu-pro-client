import mock
import pytest

from uaclient import exceptions
from uaclient.api.u.pro.security.vulnerabilities._common.v1 import (
    ProManifestSourcePackage,
    SourcePackages,
    VulnerabilityParser,
    VulnerabilityStatus,
    _get_source_package_from_vulnerabilities_data,
    _get_vulnerability_fix_status,
)

M_PATH = "uaclient.api.u.pro.security.vulnerabilities._common.v1."


VULNERABILITIES_DATA = {
    "packages": {
        "test1": {
            "source_versions": {
                "1.1.2": {
                    "binary_packages": {
                        "test1-bin": "1.1.5",
                        "test1-bin1": "1.1.2",
                    },
                    "pocket": "esm-infra",
                },
                "1.1.3": {
                    "binary_packages": {
                        "test1-bin": "1.1.5",
                        "test1-bin1": "1.1.2",
                        "test1-bin2": "1.1.3",
                    },
                    "pocket": "esm-infra",
                },
                "1.1.4": {
                    "binary_packages": {
                        "test1-bin1": "1.1.5",
                    },
                    "pocket": "esm-infra",
                },
            },
            "cves": {
                "CVE-2022-12345": {
                    "source_fixed_version": None,
                    "status": "vulnerable",
                },
                "CVE-2022-56789": {
                    "source_fixed_version": "1.1.2",
                    "status": "fixed",
                },
                "CVE-2022-18976": {
                    "source_fixed_version": "1.0.9",
                    "status": "vulnerable",
                },
                "CVE-2022-95632": {
                    "source_fixed_version": None,
                    "status": "not-vulnerable",
                },
                "CVE-2022-86782": {
                    "source_fixed_version": "1.1.4",
                    "status": "fixed",
                },
            },
        },
        "test2": {
            "source_versions": {
                "1.1.2": {
                    "binary_packages": {
                        "test2-bin2-1": "1.1.2",
                    },
                    "pocket": "esm-infra",
                }
            },
            "cves": {
                "CVE-2022-12345": {
                    "source_fixed_version": None,
                    "status": "vulnerable",
                },
            },
        },
    },
    "security_issues": {
        "cves": {
            "CVE-2022-12345": {
                "description": "description",
                "published_at": "date",
                "notes": ["hint"],
                "mitigation": "hint",
                "cvss_severity": "low",
                "cvss_score": 4.2,
            },
            "CVE-2022-56789": {
                "description": "description",
                "published_at": "date",
                "notes": ["hint"],
                "mitigation": "hint",
                "cvss_severity": "low",
                "cvss_score": 4.2,
            },
            "CVE-2022-86782": {
                "description": "description",
                "published_at": "date",
                "notes": ["hint"],
                "mitigation": "hint",
                "cvss_severity": "low",
                "cvss_score": 4.2,
            },
        }
    },
}


class ConcreteVulnerabilityParser(VulnerabilityParser):
    vulnerability_type = "cves"

    def get_package_vulnerabilities(self, affected_pkg):
        return affected_pkg.get(self.vulnerability_type, {})

    def _post_process_vulnerability_info(
        self,
        installed_pkgs_by_source,
        vulnerability_info,
        vulnerabilities_data,
    ):
        return vulnerability_info


class TestVulnerabilityParser:

    @pytest.mark.parametrize(
        "vulnerabilities_data,installed_pkgs_by_source,expected_result",
        (
            (
                VULNERABILITIES_DATA,
                {
                    "test1": {
                        "test1-bin1": "1.1.1",
                        "test1-bin": "1.1.4",
                    }
                },
                {
                    "CVE-2022-12345": {
                        "affected_packages": [
                            {
                                "name": "test1-bin",
                                "current_version": "1.1.4",
                                "fix_version": None,
                                "status": "vulnerable",
                                "fix_available_from": None,
                            },
                            {
                                "name": "test1-bin1",
                                "current_version": "1.1.1",
                                "fix_version": None,
                                "status": "vulnerable",
                                "fix_available_from": None,
                            },
                        ],
                        "description": "description",
                        "published_at": "date",
                        "notes": ["hint"],
                        "mitigation": "hint",
                        "cvss_severity": "low",
                        "cvss_score": 4.2,
                    },
                    "CVE-2022-56789": {
                        "affected_packages": [
                            {
                                "name": "test1-bin",
                                "current_version": "1.1.4",
                                "fix_version": "1.1.5",
                                "status": "fixed",
                                "fix_available_from": "esm-infra",
                            },
                            {
                                "name": "test1-bin1",
                                "current_version": "1.1.1",
                                "fix_version": "1.1.2",
                                "status": "fixed",
                                "fix_available_from": "esm-infra",
                            },
                        ],
                        "description": "description",
                        "published_at": "date",
                        "notes": ["hint"],
                        "mitigation": "hint",
                        "cvss_severity": "low",
                        "cvss_score": 4.2,
                    },
                    "CVE-2022-86782": {
                        "affected_packages": [
                            {
                                "name": "test1-bin",
                                "current_version": "1.1.4",
                                "fix_version": None,
                                "status": "unknown",
                                "fix_available_from": None,
                            },
                            {
                                "name": "test1-bin1",
                                "current_version": "1.1.1",
                                "fix_version": "1.1.5",
                                "status": "fixed",
                                "fix_available_from": "esm-infra",
                            },
                        ],
                        "description": "description",
                        "published_at": "date",
                        "notes": ["hint"],
                        "mitigation": "hint",
                        "cvss_severity": "low",
                        "cvss_score": 4.2,
                    },
                },
            ),
        ),
    )
    @mock.patch(
        M_PATH + "VulnerabilityParser._get_installed_source_pkg_version"
    )
    def test_get_vulnerabilities_for_installed_pkgs(
        self,
        m_get_installed_source_pkg_version,
        vulnerabilities_data,
        installed_pkgs_by_source,
        expected_result,
    ):
        m_get_installed_source_pkg_version.return_value = "1.1.3"
        parser = ConcreteVulnerabilityParser()
        assert (
            parser.get_vulnerabilities_for_installed_pkgs(
                vulnerabilities_data, installed_pkgs_by_source
            )
            == expected_result
        )


class TestGetVulnerabilityFixStatus:
    @pytest.mark.parametrize(
        "affected_pkgs,expected_state",
        (
            (
                [
                    {
                        "fix_version": "1.0",
                        "name": "pkg1",
                    },
                    {
                        "fix_version": "1.0",
                        "name": "pkg2",
                    },
                ],
                VulnerabilityStatus.FULL_FIX_AVAILABLE,
            ),
            (
                [
                    {
                        "fix_version": None,
                        "name": "pkg1",
                    },
                    {
                        "fix_version": "1.0",
                        "name": "pkg2",
                    },
                ],
                VulnerabilityStatus.PARTIAL_FIX_AVAILABLE,
            ),
            (
                [
                    {
                        "fix_version": None,
                        "name": "pkg1",
                    },
                    {
                        "fix_version": None,
                        "name": "pkg2",
                    },
                ],
                VulnerabilityStatus.NO_FIX_AVAILABLE,
            ),
        ),
    )
    def test_get_vulnerability_fix_status(
        self,
        affected_pkgs,
        expected_state,
    ):
        assert _get_vulnerability_fix_status(affected_pkgs) == expected_state


class TestGetSourcePackageFromVulnerabilitiesData:
    @pytest.mark.parametrize(
        "vulnerabilities_data,bin_pkg,expected_source_pkg",
        (
            (
                VULNERABILITIES_DATA,
                "test1-bin1",
                "test1",
            ),
            (
                VULNERABILITIES_DATA,
                "test1-bin",
                "test1",
            ),
            (
                VULNERABILITIES_DATA,
                "test1-bin2",
                "test1",
            ),
            (
                VULNERABILITIES_DATA,
                "non-existant",
                "",
            ),
        ),
    )
    def test_get_source_package_from_vulnerabilities(
        self,
        vulnerabilities_data,
        bin_pkg,
        expected_source_pkg,
    ):
        assert (
            _get_source_package_from_vulnerabilities_data(
                vulnerabilities_data, bin_pkg
            )
            == expected_source_pkg
        )


class TestProManifestSourcePackage:
    @pytest.mark.parametrize(
        "manifest_content,expected_value",
        (
            (
                ("pkg1\t1.1.2\n" "pkg2-2:amd64\t3.2+1git1\n" "invalid"),
                False,
            ),
        ),
    )
    def test_invalid_manifest(self, manifest_content, expected_value, tmpdir):
        manifest_file = tmpdir.join("manifest")
        manifest_file.write(manifest_content)

        with pytest.raises(exceptions.ManifestParseError):
            ProManifestSourcePackage.parse(manifest_file.strpath)

    @pytest.mark.parametrize(
        "manifest_content,expected_value",
        (
            (
                (
                    "pkg1\t1.1.2\n"
                    "pkg2-2:amd64\t3.2+1git1\n"
                    "pkg3.1.0\t1.1\n"
                    "pkg4++:amd64\t1.2\n"
                    "snap:pkg5\tlatest/stable\t1725\n"
                    "snap:pkg6\tlatest/stable\t1113"
                ),
                {
                    "pkg1": "1.1.2",
                    "pkg2-2": "3.2+1git1",
                    "pkg3.1.0": "1.1",
                    "pkg4++": "1.2",
                },
            ),
        ),
    )
    def test_parse(self, manifest_content, expected_value, tmpdir):
        manifest_file = tmpdir.join("manifest")
        manifest_file.write(manifest_content)

        assert (
            ProManifestSourcePackage.parse(manifest_file.strpath)
            == expected_value
        )


class TestSourcePackages:

    @pytest.mark.parametrize(
        "manifest_content,vulnerabilities_data,expected_data",
        (
            (
                (
                    "test1-bin\t1.1.2\n"
                    "test1-bin1:amd64\t3.2+1git1\n"
                    "test2-bin2-1\t1.1\n"
                    "snap:pkg5\tlatest/stable\t1725\n"
                    "snap:pkg6\tlatest/stable\t1113"
                ),
                VULNERABILITIES_DATA,
                {
                    "test1": {
                        "test1-bin": "1.1.2",
                        "test1-bin1": "3.2+1git1",
                    },
                    "test2": {"test2-bin2-1": "1.1"},
                },
            ),
        ),
    )
    def test_parse_manifest_file(
        self, manifest_content, vulnerabilities_data, expected_data, tmpdir
    ):
        manifest_file = tmpdir.join("manifest")
        manifest_file.write(manifest_content)

        assert (
            expected_data
            == SourcePackages(
                manifest_file=manifest_file.strpath,
                vulnerabilities_data=vulnerabilities_data,
            ).get()
        )
