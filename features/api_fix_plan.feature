Feature: Fix plan API endpoints

    @series.xenial
    @series.bionic
    @series.focal
    @series.jammy
    @uses.config.machine_type.lxd-container
    Scenario Outline: Fix command on an unattached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get update` with sudo
        And I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-1800-123456"]}'` as non-root
        Then stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"error": {"code": "security-fix-not-found-issue", "msg": "Error: CVE-1800-123456 not found."}, "expected_status": "error", "plan": \[\], "title": "CVE-1800-123456", "warnings": \[\]}\], "expected_status": "error"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixPlan"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-123455", "CVE-12"]}'` as non-root
        Then stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"error": {"code": "invalid-security-issue", "msg": "Error: issue \\"CVE-123455\\" is not recognized.\\n\\nCVE should follow the pattern CVE-yyyy-nnn.\\n\\nUSN should follow the pattern USN-nnnn."}, "expected_status": "error", "plan": \[\], "title": "CVE-123455", "warnings": \[\]}, {"error": {"code": "invalid-security-issue", "msg": "Error: issue \\"CVE-12\\" is not recognized.\\n\\nCVE should follow the pattern CVE-yyyy-nnn.\\n\\nUSN should follow the pattern USN-nnnn."}, "expected_status": "error", "plan": \[\], "title": "CVE-12", "warnings": \[\]}\], "expected_status": "error"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixPlan"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """

        Examples: ubuntu release details
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | jammy   |

    @series.focal
    @uses.config.machine_type.lxd-container
    Scenario Outline: Fix command on an unattached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-2020-28196"]}'` as non-root
        Then stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"error": null, "expected_status": "fixed", "plan": \[{"data": {"status": "cve-already-fixed"}, "operation": "no-op", "order": 1}\], "title": "CVE-2020-28196", "warnings": \[\]}\], "expected_status": "fixed"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixPlan"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-2022-24959"]}'` as non-root
        Then stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"error": null, "expected_status": "not-affected", "plan": \[{"data": {"status": "system-not-affected"}, "operation": "no-op", "order": 1}], "title": "CVE-2022-24959", "warnings": \[\]}\], "expected_status": "not-affected"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixPlan"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-2020-28196", "CVE-2022-24959"]}'` as non-root
        Then stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"error": null, "expected_status": "fixed", "plan": \[{"data": {"status": "cve-already-fixed"}, "operation": "no-op", "order": 1}\], "title": "CVE-2020-28196", "warnings": \[\]}, {"error": null, "expected_status": "not-affected", "plan": \[{"data": {"status": "system-not-affected"}, "operation": "no-op", "order": 1}], "title": "CVE-2022-24959", "warnings": \[\]}\], "expected_status": "fixed"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixPlan"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """


        Examples: ubuntu release details
           | release |
           | focal   |

    @series.xenial
    @uses.config.machine_type.lxd-container
    Scenario Outline: Fix command on an unattached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-2020-15180"]}'` as non-root
        Then stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"error": null, "expected_status": "not-affected", "plan": \[{"data": {"status": "system-not-affected"}, "operation": "no-op", "order": 1}], "title": "CVE-2020-15180", "warnings": \[\]}\], "expected_status": "not-affected"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixPlan"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-2020-28196"]}'` as non-root
        Then stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"error": null, "expected_status": "fixed", "plan": \[{"data": {"status": "cve-already-fixed"}, "operation": "no-op", "order": 1}\], "title": "CVE-2020-28196", "warnings": \[\]}\], "expected_status": "fixed"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixPlan"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `apt-get update` with sudo
        And I run `DEBIAN_FRONTEND=noninteractive apt-get install -y expat=2.1.0-7 swish-e matanza ghostscript` with sudo
        And I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-2017-9233"]}'` as non-root
        Then stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"error": null, "expected_status": "still-affected", "plan": \[{"data": {"binary_packages": \["expat"\], "source_packages": \["expat"\]}, "operation": "apt-upgrade", "order": 2}\], "title": "CVE-2017-9233", "warnings": \[{"data": {"source_packages": \["matanza", "swish-e"\], "status": "needs-triage"}, "order": 1, "warning_type": "security-issue-not-fixed"}\]}\], "expected_status": "still-affected"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixPlan"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-2020-28196", "CVE-2020-15180", "CVE-2017-9233"]}'` as non-root
        Then stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"error": null, "expected_status": "fixed", "plan": \[{"data": {"status": "cve-already-fixed"}, "operation": "no-op", "order": 1}\], "title": "CVE-2020-28196", "warnings": \[\]}, {"error": null, "expected_status": "not-affected", "plan": \[{"data": {"status": "system-not-affected"}, "operation": "no-op", "order": 1}\], "title": "CVE-2020-15180", "warnings": \[\]}, {"error": null, "expected_status": "still\-affected", "plan": \[{"data": {"binary_packages": \["expat"\], "source_packages": \["expat"\]}, "operation": "apt-upgrade", "order": 2}\], "title": "CVE-2017-9233", "warnings": \[{"data": {"source_packages": \["matanza", "swish\-e"\], "status": "needs-triage"}, "order": 1, "warning_type": "security\-issue-not\-fixed"}\]}\], "expected_status": "still\-affected"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixPlan"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """

        Examples: ubuntu release details
           | release |
           | xenial  |

    @series.bionic
    @uses.config.machine_type.lxd-container
    Scenario Outline: Fix command on an unattached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-2020-28196"]}'` as non-root
        Then stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"error": null, "expected_status": "fixed", "plan": \[{"data": {"status": "cve-already-fixed"}, "operation": "no-op", "order": 1}\], "title": "CVE-2020-28196", "warnings": \[\]}\], "expected_status": "fixed"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixPlan"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `apt-get update` with sudo
        And I run `apt-get install xterm=330-1ubuntu2 -y` with sudo
        And I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-2021-27135"]}'` as non-root
        Then stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"error": null, "expected_status": "fixed", "plan": \[{"data": {"binary_packages": \["xterm"\], "source_packages": \["xterm"\]}, "operation": "apt-upgrade", "order": 1}\], "title": "CVE-2021-27135", "warnings": \[\]}\], "expected_status": "fixed"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixPlan"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """

        Examples: ubuntu release details
           | release |
           | bionic  |
