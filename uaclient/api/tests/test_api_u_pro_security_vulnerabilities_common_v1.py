import pytest

from uaclient.api.u.pro.security.vulnerabilities._common.v1 import (
    ProManifestSourcePackage,
    SourcePackages,
    VulnerabilityParser,
    VulnerabilityStatus,
    _get_source_package_from_vulnerabilities_data,
    _get_vulnerability_fix_status,
)

VULNERABILITIES_DATA = {
    "packages": {
        "test1": {
            "source_versions": {
                "1.1.2": {
                    "binary_packages": {
                        "test1-bin": "1.1.2",
                        "test1-bin1": "1.1.2",
                    },
                    "pocket": "esm-infra",
                }
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
        }
    },
}


class ConcreteVulnerabilityParser(VulnerabilityParser):
    vulnerability_type = "cves"

    def get_package_vulnerabilities(self, affected_pkg):
        return affected_pkg.get(self.vulnerability_type, {})


class TestVulnerabilityParser:

    @pytest.mark.parametrize(
        "vulnerabilities_data,installed_pkgs_by_source,expected_result",
        (
            (
                VULNERABILITIES_DATA,
                {
                    "test1": {
                        "test1-bin1": "1.1.1",
                        "test1-bin": "1.1.1",
                    }
                },
                {
                    "CVE-2022-12345": {
                        "affected_packages": [
                            {
                                "name": "test1-bin",
                                "current_version": "1.1.1",
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
                                "current_version": "1.1.1",
                                "fix_version": "1.1.2",
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
                },
            ),
        ),
    )
    def test_parse_data(
        self, vulnerabilities_data, installed_pkgs_by_source, expected_result
    ):
        parser = ConcreteVulnerabilityParser()
        parser.parse_data(vulnerabilities_data, installed_pkgs_by_source)
        assert parser.vulnerabilities == expected_result


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
                (
                    "pkg1\t1.1.2\n"
                    "pkg2-2:amd64\t3.2+1git1\n"
                    "pkg3.1.0\t1.1\n"
                    "pkg4++:amd64\t1.2\n"
                    "snap:pkg5\tlatest/stable\t1725\n"
                    "snap:pkg6\tlatest/stable\t1113"
                ),
                True,
            ),
            (
                ("pkg1\t1.1.2\n" "pkg2-2:amd64\t3.2+1git1\n" "invalid"),
                False,
            ),
        ),
    )
    def test_valid(self, manifest_content, expected_value, tmpdir):
        manifest_file = tmpdir.join("manifest")
        manifest_file.write(manifest_content)

        assert (
            ProManifestSourcePackage.valid(manifest_file.strpath)
            is expected_value
        )

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
