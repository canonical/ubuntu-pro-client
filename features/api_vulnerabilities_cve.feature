Feature: Client behaviour for CVE vulnerabilities API

  @uses.config.contract_token
  Scenario Outline: CVE vulnerabilities for xenial machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I verify that running `pro api u.pro.security.vulnerabilities.cve.v1 --args series=jammy` `as non-root` exits `1`
    Then API errors field output is:
      """
      [
        {
          "code": "dependent-option",
          "meta": {
            "option1": "series",
            "option2": "manifest_file"
          },
          "title": "Error: series depends on manifest_file to work properly."
        }
      ]
      """
    When I attach `contract_token` with sudo
    # Check we can download and parse the JSON data
    And I run `pro api u.pro.security.vulnerabilities.cve.v1` as non-root
    And I push static file `security_issues_xenial.json` to machine
    And I run `pro api u.pro.security.vulnerabilities.cve.v1 --args data_file=/tmp/security_issues_xenial.json` as non-root
    And I apply this jq filter `.data.attributes.cves[] | select(.name == "CVE-2022-2286")` to the output
    Then stdout matches regexp:
      """
      {
        "affected_packages": \[
          {
            "current_version": ".*",
            "fix_available_from": "esm\-infra",
            "fix_status": "fixed",
            "fix_version": ".*",
            "name": "vim"
          },
          {
            "current_version": ".*",
            "fix_available_from": "esm\-infra",
            "fix_status": "fixed",
            "fix_version": ".*",
            "name": "vim\-common"
          },
          {
            "current_version": ".*",
            "fix_available_from": "esm\-infra",
            "fix_status": "fixed",
            "fix_version": ".*",
            "name": "vim\-runtime"
          },
          {
            "current_version": ".*",
            "fix_available_from": "esm\-infra",
            "fix_status": "fixed",
            "fix_version": ".*",
            "name": "vim\-tiny"
          }
        ],
        "cvss_score": 7.8,
        "cvss_severity": "high",
        "description": ".*",
        "fixable": "yes",
        "name": "CVE-2022-2286",
        "notes": \[\],
        "published_at": ".*",
        "related_usns": \[
          {
            "affected_installed_packages": \[
              "vim"
            \],
            "name": "USN-6270-1",
            "title": "Vim vulnerabilities"
          }
        \],
        "ubuntu_priority": "low"
      }
      """
    When I apt install `vim`
    And I run `pro api u.pro.security.vulnerabilities.cve.v1 --args data_file=/tmp/security_issues_xenial.json` as non-root
    And I apply this jq filter `.data.attributes.cves` to the output
    Then stdout does not contain substring:
      """
      "name": "CVE-2022-2286"
      """
    When I run `pro api u.pro.security.vulnerabilities.cve.v1 --data '{"all": true, "data_file": "/tmp/security_issues_xenial.json"}'` as non-root
    And I apply this jq filter `.data.attributes.cves[] | select (.name == "CVE-2017-11544")` to the output
    Then stdout matches regexp:
      """
      {
        "affected_packages": \[
          {
            "current_version": ".*",
            "fix_available_from": null,
            "fix_status": "vulnerable",
            "fix_version": null,
            "name": "tcpdump"
          }
        \],
        "cvss_score": null,
        "cvss_severity": null,
        "description": ".*",
        "fixable": "no",
        "name": "CVE-2017-11544",
        "notes": \[
          .*
        \],
        "published_at": ".*",
        "related_usns": \[\],
        "ubuntu_priority": "medium"
      }
      """
    When I run `pro api u.pro.security.vulnerabilities.cve.v1 --data '{"unfixable": true, "data_file": "/tmp/security_issues_xenial.json"}'` as non-root
    And I apply this jq filter `.data.attributes.cves[] | select (.name == "CVE-2017-11544")` to the output
    Then stdout matches regexp:
      """
      {
        "affected_packages": \[
          {
            "current_version": ".*",
            "fix_available_from": null,
            "fix_status": "vulnerable",
            "fix_version": null,
            "name": "tcpdump"
          }
        \],
        "cvss_score": null,
        "cvss_severity": null,
        "description": ".*",
        "fixable": "no",
        "name": "CVE-2017-11544",
        "notes": \[
          .*
        \],
        "published_at": ".*",
        "related_usns": \[\],
        "ubuntu_priority": "medium"
      }
      """
    When I verify that running `pro api u.pro.security.vulnerabilities.cve.v1 --data '{"unfixable": true, "all": true, "data_file": "/tmp/security_issues_xenial.json"}'` `as non-root` exits `1`
    Then API errors field output is:
      """
      [
        {
          "code": "invalid-option-combination",
          "meta": {
            "option1": "unfixable",
            "option2": "all"
          },
          "title": "Error: Cannot use unfixable together with all."
        }
      ]
      """
    When I create the file `/tmp/manifest` with the following:
      """
      libzstd1:amd64     1.3.1+dfsg-1~ubuntu0.16.04.1
      """
    And I run `pro api u.pro.security.vulnerabilities.cve.v1 --args data_file=/tmp/security_issues_xenial.json manifest_file=/tmp/manifest` as non-root
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "apt_updated_at": null,
          "cves": [
            {
              "affected_packages": [
                {
                  "current_version": "1.3.1\+dfsg\-1~ubuntu0.16.04.1",
                  "fix_available_from": "esm-infra",
                  "fix_status": "fixed",
                  "fix_version": "1.3.1\+dfsg\-1~ubuntu0.16.04.1\+esm1",
                  "name": "libzstd1"
                }
              ],
              "cvss_score": 8.1,
              "cvss_severity": "high",
              "description": ".*",
              "fixable": "yes",
              "name": "CVE-2019-11922",
              "notes": [],
              "published_at": ".*",
              "related_usns": [
                {
                  "affected_installed_packages": [],
                  "name": "USN-4108-1",
                  "title": ""
                },
                {
                  "affected_installed_packages": [
                    "libzstd"
                  ],
                  "name": "USN-5593-1",
                  "title": "Zstandard vulnerability"
                }
              ],
              "ubuntu_priority": "medium"
            }
          ],
          "vulnerability_data_published_at": ".*"
        },
        "meta": {
          "environment_vars": []
        },
        "type": "CVEVulnerabilities"
      }
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
