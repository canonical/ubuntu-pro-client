Feature: Client behaviour for CVE vulnerabilities API

  Scenario Outline: CVE vulnerabilities for xenial machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I apt update
    And I apt install `jq`
    And I run shell command `pro api u.pro.security.vulnerabilities.cve.v1 | jq .data.attributes.cves` as non-root
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
          "published_at": ".*"
        },
      """
      When I run shell command `pro api u.pro.security.vulnerabilities.cve.v1 --data '{\"all\": true}' | jq .data.attributes.cves` as non-root
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
          "published_at": ".*"
        },
      """
      When I run shell command `pro api u.pro.security.vulnerabilities.cve.v1 --data '{\"unfixable\": true}' | jq .data.attributes.cves` as non-root
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
          "published_at": ".*"
        },
      """
      And stdout does not match regexp:
      """
      "fixable": "yes"
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
