Feature: Client behaviour for CVE vulnerabilities API

  @uses.config.contract_token
  Scenario Outline: CVE vulnerabilities for xenial machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    # Check we can download and parse the JSON data
    And I run `pro api u.pro.security.vulnerabilities.cve.v1` as non-root
    And I push static file `security_issues_xenial.bz2` to machine
    And I run `bzip2 -d /tmp/security_issues_xenial.bz2` as non-root
    And I apt install `jq`
    And I run shell command `pro api u.pro.security.vulnerabilities.cve.v1 --args data_file=/tmp/security_issues_xenial | jq .data.attributes.cves` as non-root
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
          "ubuntu_priority": "low"
        },
      """
    When I apt install `vim`
    And I run shell command `pro api u.pro.security.vulnerabilities.cve.v1 --args data_file=/tmp/security_issues_xenial | jq .data.attributes.cves` as non-root
    Then stdout does not match regexp:
    """
    "name": "CVE-2022-2286"
    """
    When I run shell command `pro api u.pro.security.vulnerabilities.cve.v1 --data '{\"all\": true, \"data_file\": \"/tmp/security_issues_xenial\"}' | jq .data.attributes.cves` as non-root
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
        "ubuntu_priority": "medium"
      },
    """
    When I run shell command `pro api u.pro.security.vulnerabilities.cve.v1 --data '{\"unfixable\": true, \"data_file\": \"/tmp/security_issues_xenial\"}' | jq .data.attributes.cves` as non-root
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
        "ubuntu_priority": "medium"
      },
    """
    And stdout does not match regexp:
    """
    "fixable": "yes"
    """
    When I create the file `/tmp/manifest` with the following:
    """
    libzstd1:amd634     1.3.1+dfsg-1~ubuntu0.16.04.1
    """
    And I run `pro api u.pro.security.vulnerabilities.cve.v1 --args data_file=/tmp/security_issues_xenial manifest_file=/tmp/manifest` as non-root
    Then API data field output matches regexp:
    """
    {
      "attributes": {
        "apt_updated_at": ".*",
        "cves": [
          {
            "affected_packages": [
              {
                "current_version": "1.3.1\+dfsg\-1~ubuntu0.16.04.1",
                "fix_available_from": "esm-infra",
                "fix_status": "fixed",
                "fix_version": ".*",
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
