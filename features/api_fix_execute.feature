Feature: Fix execute API endpoints

    @series.lts
    Scenario Outline: Fix execute command on invalid CVEs/USNs
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I run `pro api u.pro.security.fix.cve.execute.v1 --data '{"cves": ["CVE-1800-123456"]}'` as non-root
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `cve_fix_execute` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"description": null, "errors": \[{"error_type": "security-fix-not-found-issue", "failed_upgrades": null, "reason": "Error: CVE-1800-123456 not found."}\], "status": "error", "title": "CVE-1800-123456", "upgraded_packages": \[\]}\], "status": "error"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.usn.execute.v1 --data '{"usns": ["USN-123455"]}'` as non-root
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `usn_fix_execute` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"usns_data": {"status": "error", "usns": \[{"related_usns": \[\], "target_usn": {"description": null, "errors": \[{"error_type": "invalid-security-issue", "failed_upgrades": null, "reason": "Error: issue \\"USN-123455\\" is not recognized.\\n\\nCVEs should follow the pattern CVE-yyyy-nnn.\\n\\nUSNs should follow the pattern USN-nnnn."}\], "status": "error", "title": "USN-123455", "upgraded_packages": \[\]}}\]}}, "meta": {"environment_vars": \[\]}, "type": "USNFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.cve.execute.v1 --data '{"cves": ["CVE-123455", "CVE-12"]}'` as non-root
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `cve_fix_execute` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"description": null, "errors": \[{"error_type": "invalid-security-issue", "failed_upgrades": null, "reason": "Error: issue \\"CVE-123455\\" is not recognized.\\n\\nCVEs should follow the pattern CVE-yyyy-nnn.\\n\\nUSNs should follow the pattern USN-nnnn."}\], "status": "error", "title": "CVE-123455", "upgraded_packages": \[\]}, {"description": null, "errors": \[{"error_type": "invalid-security-issue", "failed_upgrades": null, "reason": "Error: issue \\"CVE-12\\" is not recognized.\\n\\nCVEs should follow the pattern CVE-yyyy-nnn.\\n\\nUSNs should follow the pattern USN-nnnn."}\], "status": "error", "title": "CVE-12", "upgraded_packages": \[\]}\], "status": "error"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.usn.execute.v1 --data '{"usns": ["USN-123455", "USN-12"]}'` as non-root
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `usn_fix_execute` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"usns_data": {"status": "error", "usns": \[{"related_usns": \[\], "target_usn": {"description": null, "errors": \[{"error_type": "invalid-security-issue", "failed_upgrades": null, "reason": "Error: issue \\"USN-123455\\" is not recognized.\\n\\nCVEs should follow the pattern CVE-yyyy-nnn.\\n\\nUSNs should follow the pattern USN-nnnn."}\], "status": "error", "title": "USN-123455", "upgraded_packages": \[\]}}, {"related_usns": \[\], "target_usn": {"description": null, "errors": \[{"error_type": "invalid-security-issue", "failed_upgrades": null, "reason": "Error: issue \\"USN-12\\" is not recognized.\\n\\nCVEs should follow the pattern CVE-yyyy-nnn.\\n\\nUSNs should follow the pattern USN-nnnn."}\], "status": "error", "title": "USN-12", "upgraded_packages": \[\]}}\]}}, "meta": {"environment_vars": \[\]}, "type": "USNFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """

        Examples: ubuntu release details
           | release | machine_type  |
           | xenial  | lxd-container |
           | bionic  | lxd-container |
           | focal   | lxd-container |
           | jammy   | lxd-container |

    @series.focal
    Scenario Outline: Fix execute on a Focal machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I run `pro api u.pro.security.fix.cve.execute.v1 --data '{"cves": ["CVE-2020-28196"]}'` as non-root
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `cve_fix_execute` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"description": "Kerberos vulnerability", "errors": null, "status": "fixed", "title": "CVE-2020-28196", "upgraded_packages": \[\]}\], "status": "fixed"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.cve.execute.v1 --data '{"cves": ["CVE-2022-24959"]}'` as non-root
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `cve_fix_execute` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"description": "Linux kernel vulnerabilities", "errors": null, "status": "not-affected", "title": "CVE-2022-24959", "upgraded_packages": \[\]}\], "status": "not-affected"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.cve.execute.v1 --data '{"cves": ["CVE-2020-28196", "CVE-2022-24959"]}'` as non-root
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `cve_fix_execute` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"description": "Kerberos vulnerability", "errors": null, "status": "fixed", "title": "CVE-2020-28196", "upgraded_packages": \[\]}, {"description": "Linux kernel vulnerabilities", "errors": null, "status": "not-affected", "title": "CVE-2022-24959", "upgraded_packages": \[\]}\], "status": "fixed"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `apt-get update` with sudo
        And I run `apt install -y libawl-php=0.60-1 --allow-downgrades` with sudo
        And I run `pro api u.pro.security.fix.usn.execute.v1 --data '{"usns": ["USN-4539-1"]}'` as non-root
        Then stdout is a json matching the `api_response` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"usns_data": {"status": "error", "usns": \[{"related_usns": \[\], "target_usn": {"description": "AWL vulnerability", "errors": \[{"error_type": "fix-require-root", "failed_upgrades": \[{"name": "awl", "pocket": "standard-updates"}\], "reason": "Package fixes cannot be installed.\\nTo install them, run this command as root \(try using sudo\)"}\], "status": "error", "title": "USN-4539-1", "upgraded_packages": \[\]}}\]}}, "meta": {"environment_vars": \[\]}, "type": "USNFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]
        """
        When I run `pro api u.pro.security.fix.usn.execute.v1 --data '{"usns": ["USN-4539-1"]}'` with sudo
        Then stdout is a json matching the `api_response` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"usns_data": {"status": "fixed", "usns": \[{"related_usns": \[\], "target_usn": {"description": "AWL vulnerability", "errors": null, "status": "fixed", "title": "USN-4539-1", "upgraded_packages": \[{"name": "libawl-php", "pocket": "standard-updates", "version": ".*"}\]}}\]}}, "meta": {"environment_vars": \[\]}, "type": "USNFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.usn.execute.v1 --data '{"usns": ["USN-4539-1"]}'` with sudo
        Then stdout is a json matching the `api_response` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"usns_data": {"status": "fixed", "usns": \[{"related_usns": \[\], "target_usn": {"description": "AWL vulnerability", "errors": null, "status": "fixed", "title": "USN-4539-1", "upgraded_packages": \[\]}}\]}}, "meta": {"environment_vars": \[\]}, "type": "USNFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `apt install -y rsync=3.1.3-8 --allow-downgrades` with sudo
        And I run `apt install -y zlib1g=1:1.2.11.dfsg-2ubuntu1 --allow-downgrades` with sudo
        And I run `pro api u.pro.security.fix.usn.execute.v1 --data '{"usns": ["USN-5573-1"]}'` with sudo
        Then stdout is a json matching the `api_response` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"usns_data": {"status": "fixed", "usns": \[{"related_usns": \[{"description": "zlib vulnerability", "errors": null, "status": "not-affected", "title": "USN-5570-1", "upgraded_packages": \[\]}, {"description": "zlib vulnerability", "errors": null, "status": "fixed", "title": "USN-5570-2", "upgraded_packages": \[{"name": "zlib1g", "pocket": "standard-updates", "version": ".*"}\]}\], "target_usn": {"description": "rsync vulnerability", "errors": null, "status": "fixed", "title": "USN-5573-1", "upgraded_packages": \[{"name": "rsync", "pocket": "standard-updates", "version": ".*"}\]}}\]}}, "meta": {"environment_vars": \[\]}, "type": "USNFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.usn.execute.v1 --data '{"usns": ["USN-4539-1", "USN-5573-1"]}'` as non-root
        Then stdout is a json matching the `api_response` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"usns_data": {"status": "fixed", "usns": \[{"related_usns": \[\], "target_usn": {"description": "AWL vulnerability", "errors": null, "status": "fixed", "title": "USN-4539-1", "upgraded_packages": \[\]}}, {"related_usns": \[{"description": "zlib vulnerability", "errors": null, "status": "not-affected", "title": "USN-5570-1", "upgraded_packages": \[\]}, {"description": "zlib vulnerability", "errors": null, "status": "fixed", "title": "USN-5570-2", "upgraded_packages": \[\]}\], "target_usn": {"description": "rsync vulnerability", "errors": null, "status": "fixed", "title": "USN-5573-1", "upgraded_packages": \[\]}}\]}}, "meta": {"environment_vars": \[\]}, "type": "USNFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """

        Examples: ubuntu release details
           | release | machine_type  |
           | focal   | lxd-container |

    @series.xenial
    Scenario Outline: Fix execute API command on a Xenial machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I run `pro api u.pro.security.fix.cve.execute.v1 --data '{"cves": ["CVE-2020-15180"]}'` as non-root
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `cve_fix_execute` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"description": ".*", "errors": null, "status": "not-affected", "title": "CVE-2020-15180", "upgraded_packages": \[\]}\], "status": "not-affected"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.cve.execute.v1 --data '{"cves": ["CVE-2020-28196"]}'` as non-root
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `cve_fix_execute` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"description": ".*", "errors": null, "status": "fixed", "title": "CVE-2020-28196", "upgraded_packages": \[\]}\], "status": "fixed"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `apt-get update` with sudo
        And I run `DEBIAN_FRONTEND=noninteractive apt-get install -y expat=2.1.0-7 swish-e matanza ghostscript` with sudo
        And I run `pro api u.pro.security.fix.cve.execute.v1 --data '{"cves": ["CVE-2017-9233"]}'` as non-root
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `cve_fix_execute` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"description": ".*", "errors": \[{"error_type": "security-issue-not-fixed", "failed_upgrades": \[{"name": "matanza", "pocket": null}, {"name": "swish-e", "pocket": null}\], "reason": "Ubuntu security engineers are investigating this issue."}, {"error_type": "fix-require-root", "failed_upgrades": \[{"name": "expat", "pocket": "standard-updates"}\], "reason": "Package fixes cannot be installed.\\nTo install them, run this command as root \(try using sudo\)"}\], "status": "error", "title": "CVE-2017-9233", "upgraded_packages": \[\]}\], "status": "error"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.cve.execute.v1 --data '{"cves": ["CVE-2017-9233"]}'` with sudo
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `cve_fix_execute` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"description": ".*", "errors": \[{"error_type": "security-issue-not-fixed", "failed_upgrades": \[{"name": "matanza", "pocket": null}, {"name": "swish-e", "pocket": null}\], "reason": "Ubuntu security engineers are investigating this issue."}\], "status": "still-affected", "title": "CVE-2017-9233", "upgraded_packages": \[{"name": "expat", "pocket": "standard-updates", "version": ".*"}\]}\], "status": "still-affected"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-2020-28196", "CVE-2020-15180", "CVE-2017-9233"]}'` as non-root
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `cve_fix_execute` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"additional_data": {}, "affected_packages": \["krb5"\], "description": ".*", "error": null, "expected_status": "fixed", "plan": \[{"data": {"pocket": "standard-updates", "source_packages": \["krb5"\], "status": "cve-already-fixed"}, "operation": "no-op", "order": 1}\], "title": "CVE-2020-28196", "warnings": \[\]}, {"additional_data": {}, "affected_packages": \[\], "description": ".*", "error": null, "expected_status": "not-affected", "plan": \[{"data": {"status": "system-not-affected"}, "operation": "no-op", "order": 1}\], "title": "CVE-2020-15180", "warnings": \[\]}, {"additional_data": {}, "affected_packages": \["expat", "matanza", "swish-e"\], "description": ".*", "error": null, "expected_status": "still-affected", "plan": \[{"data": {"pocket": "standard-updates", "source_packages": \["expat"\], "status": "cve-already-fixed"}, "operation": "no-op", "order": 2}\], "title": "CVE-2017-9233", "warnings": \[{"data": {"source_packages": \["matanza", "swish-e"\], "status": "needs-triage"}, "order": 1, "warning_type": "security-issue-not-fixed"}\]}\], "expected_status": "still-affected"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixPlan"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]
        """
        When I run `apt install -y libawl-php` with sudo
        And I reboot the machine
        And I run `pro api u.pro.security.fix.usn.execute.v1 --data '{"usns": ["USN-4539-1"]}'` as non-root
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `usn_fix_execute` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"usns_data": {"status": "not-affected", "usns": \[{"related_usns": \[\], "target_usn": {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-4539-1", "upgraded_packages": \[\]}}\]}}, "meta": {"environment_vars": \[\]}, "type": "USNFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.usn.execute.v1 --data '{"usns": ["USN-5079-2"]}'` as non-root
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `usn_fix_execute` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"usns_data": {"status": "still-affected", "usns": \[{"related_usns": null, "target_usn": {"description": ".*", "errors": \[{"error_type": "fix-requires-attach", "failed_upgrades": \[{"name": "curl", "pocket": "esm-infra"}\], "reason": "The update is not installed because this system is not attached to a\\nsubscription.\\n"}\], "status": "still-affected", "title": "USN-5079-2", "upgraded_packages": \[\]}}\]}}, "meta": {"environment_vars": \[\]}, "type": "USNFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I attach `contract_token` with sudo
        And I run `pro api u.pro.security.fix.usn.execute.v1 --data '{"usns": ["USN-5079-2"]}'` with sudo
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `usn_fix_execute` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"usns_data": {"status": "fixed", "usns": \[{"related_usns": \[{"description": ".*", "errors": null, "status": "not-affected", "title": "USN-5079-1", "upgraded_packages": \[\]}\], "target_usn": {"description": "curl vulnerabilities", "errors": null, "status": "fixed", "title": "USN-5079-2", "upgraded_packages": \[{"name": "curl", "pocket": "esm-infra", "version": ".*"}, {"name": "libcurl3-gnutls", "pocket": "esm-infra", "version": ".*"}\]}}\]}}, "meta": {"environment_vars": \[\]}, "type": "USNFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.usn.execute.v1 --data '{"usns": ["USN-5051-2"]}'` with sudo
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `usn_fix_execute` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"usns_data": {"status": "fixed", "usns": \[{"related_usns": \[{"description": ".*", "errors": null, "status": "not-affected", "title": "USN-5051-1", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-5051-3", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-5088-1", "upgraded_packages": \[\]}\], "target_usn": {"description": ".*", "errors": null, "status": "fixed", "title": "USN-5051-2", "upgraded_packages": \[{"name": "libssl1.0.0", "pocket": "esm-infra", "version": ".*"}, {"name": "openssl", "pocket": "esm-infra", "version": ".*"}\]}}\]}}, "meta": {"environment_vars": \[\]}, "type": "USNFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.usn.execute.v1 --data '{"usns": ["USN-5378-4"]}'` with sudo
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `usn_fix_execute` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"usns_data": {"status": "fixed", "usns": \[{"related_usns": \[{"description": ".*", "errors": null, "status": "not-affected", "title": "USN-5378-1", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-5378-2", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "fixed", "title": "USN-5378-3", "upgraded_packages": \[{"name": "liblzma5", "pocket": "esm-infra", "version": ".*"}, {"name": "xz-utils", "pocket": "esm-infra", "version": ".*"}\]}\], "target_usn": {"description": ".*", "errors": null, "status": "fixed", "title": "USN-5378-4", "upgraded_packages": \[{"name": "gzip", "pocket": "esm-infra", "version": ".*"}\]}}\]}}, "meta": {"environment_vars": \[\]}, "type": "USNFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.usn.execute.v1 --data '{"usns": ["USN-5051-2", "USN-5378-4"]}'` with sudo
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `usn_fix_execute` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"usns_data": {"status": "fixed", "usns": \[{"related_usns": \[{"description": ".*", "errors": null, "status": "not-affected", "title": "USN-5051-1", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-5051-3", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-5088-1", "upgraded_packages": \[\]}\], "target_usn": {"description": ".*", "errors": null, "status": "fixed", "title": "USN-5051-2", "upgraded_packages": \[\]}}, {"related_usns": \[{"description": ".*", "errors": null, "status": "not-affected", "title": "USN-5378-1", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-5378-2", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "fixed", "title": "USN-5378-3", "upgraded_packages": \[\]}\], "target_usn": {"description": ".*", "errors": null, "status": "fixed", "title": "USN-5378-4", "upgraded_packages": \[\]}}\]}}, "meta": {"environment_vars": \[\]}, "type": "USNFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro detach --assume-yes` with sudo
        And I run `sed -i "/xenial-updates/d" /etc/apt/sources.list` with sudo
        And I run `sed -i "/xenial-security/d" /etc/apt/sources.list` with sudo
        And I run `apt-get update` with sudo
        And I run `apt-get install squid -y` with sudo
        And I run `pro api u.pro.security.fix.cve.execute.v1 --data '{"cves": ["CVE-2020-25097"]}'` as non-root
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `cve_fix_execute` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"description": ".*", "errors": \[{"error_type": "package-cannot-be-installed", "failed_upgrades": \[{"name": "squid", "pocket": "standard-updates"}\], "reason": "Cannot install package squid version .*"}, {"error_type": "package-cannot-be-installed", "failed_upgrades": \[{"name": "squid-common", "pocket": "standard-updates"}\], "reason": "Cannot install package squid-common version .*"}\], "status": "still-affected", "title": "CVE-2020-25097", "upgraded_packages": \[\]}\], "status": "still-affected"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """

        Examples: ubuntu release details
           | release | machine_type  |
           | xenial  | lxd-container |

    @series.bionic
    Scenario Outline: Fix execute API command on a Bionic machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I run `pro api u.pro.security.fix.cve.execute.v1 --data '{"cves": ["CVE-2020-28196"]}'` as non-root
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `cve_fix_execute` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"description": "Kerberos vulnerability", "errors": null, "status": "fixed", "title": "CVE-2020-28196", "upgraded_packages": \[\]}\], "status": "fixed"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `apt-get update` with sudo
        And I run `apt-get install xterm=330-1ubuntu2 -y` with sudo
        And I run `pro api u.pro.security.fix.cve.execute.v1 --data '{"cves": ["CVE-2021-27135"]}'` as non-root
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `cve_fix_execute` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"description": "xterm vulnerability", "errors": \[{"error_type": "fix-require-root", "failed_upgrades": \[{"name": "xterm", "pocket": "standard-updates"}\], "reason": "Package fixes cannot be installed.\\nTo install them, run this command as root \(try using sudo\)"}\], "status": "error", "title": "CVE-2021-27135", "upgraded_packages": \[\]}\], "status": "error"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.cve.execute.v1 --data '{"cves": ["CVE-2021-27135"]}'` with sudo
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `cve_fix_execute` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"cves_data": {"cves": \[{"description": "xterm vulnerability", "errors": null, "status": "fixed", "title": "CVE-2021-27135", "upgraded_packages": \[{"name": "xterm", "pocket": "standard-updates", "version": ".*"}\]}\], "status": "fixed"}}, "meta": {"environment_vars": \[\]}, "type": "CVEFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `apt install -y libawl-php` with sudo
        And I run `pro api u.pro.security.fix.usn.execute.v1 --data '{"usns": ["USN-4539-1"]}'` as non-root
        Then stdout is a json matching the `api_response` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"usns_data": {"status": "not-affected", "usns": \[{"related_usns": \[\], "target_usn": {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-4539-1", "upgraded_packages": \[\]}}\]}}, "meta": {"environment_vars": \[\]}, "type": "USNFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `apt-get install libbz2-1.0=1.0.6-8.1 -y --allow-downgrades` with sudo
        And I run `apt-get install bzip2=1.0.6-8.1 -y` with sudo
        And I run `pro api u.pro.security.fix.usn.execute.v1 --data '{"usns": ["USN-4038-3"]}'` as non-root
        Then stdout is a json matching the `api_response` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"usns_data": {"status": "error", "usns": \[{"related_usns": \[\], "target_usn": {"description": ".*", "errors": \[{"error_type": "fix-require-root", "failed_upgrades": \[{"name": "bzip2", "pocket": "standard-updates"}\], "reason": "Package fixes cannot be installed.\\nTo install them, run this command as root \(try using sudo\)"}\], "status": "error", "title": "USN-4038-3", "upgraded_packages": \[\]}}\]}}, "meta": {"environment_vars": \[\]}, "type": "USNFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.usn.execute.v1 --data '{"usns": ["USN-4038-3"]}'` with sudo
        Then stdout is a json matching the `api_response` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"usns_data": {"status": "fixed", "usns": \[{"related_usns": \[\], "target_usn": {"description": ".*", "errors": null, "status": "fixed", "title": "USN-4038-3", "upgraded_packages": \[{"name": "bzip2", "pocket": "standard-updates", "version": ".*"}, {"name": "libbz2-1.0", "pocket": "standard-updates", "version": ".*"}\]}}\]}}, "meta": {"environment_vars": \[\]}, "type": "USNFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.usn.execute.v1 --data '{"usns": ["USN-6130-1"]}'` with sudo
        Then stdout is a json matching the `api_response` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"usns_data": {"status": "not-affected", "usns": \[{"related_usns": \[{"description": ".*", "errors": null, "status": "not-affected", "title": "USN-6033-1", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-6122-1", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-6123-1", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-6124-1", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-6127-1", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-6131-1", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-6132-1", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-6135-1", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-6149-1", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-6150-1", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-6162-1", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-6173-1", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-6175-1", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-6186-1", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-6222-1", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-6256-1", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-6385-1", "upgraded_packages": \[\]}\], "target_usn": {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-6130-1", "upgraded_packages": \[\]}}\]}}, "meta": {"environment_vars": \[\]}, "type": "USNFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I run `pro api u.pro.security.fix.usn.execute.v1 --data '{"usns": ["USN-4539-1", "USN-4038-1"]}'` with sudo
        Then stdout is a json matching the `api_response` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"usns_data": {"status": "fixed", "usns": \[{"related_usns": \[\], "target_usn": {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-4539-1", "upgraded_packages": \[\]}}, {"related_usns": \[{"description": "bzip2 vulnerabilities", "errors": null, "status": "not-affected", "title": "USN-4038-2", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-4146-1", "upgraded_packages": \[\]}, {"description": ".*", "errors": null, "status": "not-affected", "title": "USN-4146-2", "upgraded_packages": \[\]}\], "target_usn": {"description": ".*", "errors": null, "status": "fixed", "title": "USN-4038-1", "upgraded_packages": \[\]}}\]}}, "meta": {"environment_vars": \[\]}, "type": "USNFixExecute"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """

        Examples: ubuntu release details
           | release | machine_type  |
           | bionic  | lxd-container |
