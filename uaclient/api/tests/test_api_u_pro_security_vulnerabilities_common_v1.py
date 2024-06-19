import pytest

from uaclient.api.u.pro.security.vulnerabilities._common.v1 import (
    VulnerabilityParser,
)


class ConcreteVulnerabilityParser(VulnerabilityParser):
    vulnerability_type = "cves"

    def get_package_vulnerabilities(self, affected_pkg):
        return affected_pkg.get(self.vulnerability_type, {})


class TestVulnerabilityParser:

    @pytest.mark.parametrize(
        "vulnerabilities_data,installed_pkgs_by_source,expected_result",
        (
            (
                {
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
                        }
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
                },
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
