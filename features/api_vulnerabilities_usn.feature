Feature: Client behaviour for USN vulnerabilities API

  @uses.config.contract_token
  Scenario Outline: USN vulnerabilities for xenial machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I verify that running `pro api u.pro.security.vulnerabilities.usn.v1 --args series=jammy` `as non-root` exits `1`
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
    And I run `pro api u.pro.security.vulnerabilities.usn.v1` as non-root
    And I push static file `security_issues_xenial.json` to machine
    And I run `pro api u.pro.security.vulnerabilities.usn.v1 --args data_file=/tmp/security_issues_xenial.json` as non-root
    And I apply this jq filter `.data.attributes.usns[] | select (.name == "USN-4976-2")` to the output
    Then stdout matches regexp:
      """
      {
        "affected_packages": \[
          {
            "current_version": ".*",
            "fix_available_from": "esm\-infra",
            "fix_version": ".*",
            "name": "dnsmasq\-base"
          }
        ],
        "description": ".*",
        "fixable": "yes",
        "name": "USN-4976-2",
        "published_at": ".*",
        "related_cves": \[
          {
            "affected_installed_packages": \[
              "dnsmasq"
            \],
            "name": "CVE-2021-3448",
            "priority": "low"
          }
        \],
        "related_launchpad_bugs": \[\]
      }
      """
    When I apt install `dnsmasq-base`
    And I run `pro api u.pro.security.vulnerabilities.usn.v1 --args data_file=/tmp/security_issues_xenial.json` as non-root
    And I apply this jq filter `.data.attributes.usns` to the output
    Then stdout does not contain substring:
      """
      "name": "USN-4976-2",
      """
    When I run `pro api u.pro.security.vulnerabilities.usn.v1 --data '{"unfixable": true, "data_file": "/tmp/security_issues_xenial.json"}'` as non-root
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "apt_updated_at": ".*",
          "usns": [],
          "vulnerability_data_published_at": ".*"
        },
        "meta": {
          "environment_vars": []
        },
        "type": "USNVulnerabilities"
      }
      """
    When I verify that running `pro api u.pro.security.vulnerabilities.usn.v1 --data '{"unfixable": true, "all": true, "data_file": "/tmp/security_issues_xenial.json"}'` `as non-root` exits `1`
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
    And I run `pro api u.pro.security.vulnerabilities.usn.v1 --args data_file=/tmp/security_issues_xenial.json manifest_file=/tmp/manifest` as non-root
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "apt_updated_at": null,
          "usns": [
            {
              "affected_packages": [
                {
                  "current_version": "1.3.1\+dfsg\-1~ubuntu0.16.04.1",
                  "fix_available_from": "esm-infra",
                  "fix_version": "1.3.1\+dfsg\-1~ubuntu0.16.04.1\+esm2",
                  "name": "libzstd1"
                }
              ],
              "description": ".*",
              "fixable": "yes",
              "name": "USN-5593-1",
              "published_at": ".*",
              "related_cves": [
                {
                  "affected_installed_packages": [
                    "libzstd"
                  ],
                  "name": "CVE-2019-11922",
                  "priority": "medium"
                }
              ],
              "related_launchpad_bugs": []
            },
            {
              "affected_packages": [
                {
                  "current_version": "1.3.1\+dfsg\-1~ubuntu0.16.04.1",
                  "fix_available_from": "esm-infra",
                  "fix_version": "1.3.1\+dfsg\-1~ubuntu0.16.04.1\+esm3",
                  "name": "libzstd1"
                }
              ],
              "description": ".*",
              "fixable": "yes",
              "name": "USN-5720-1",
              "published_at": ".*",
              "related_cves": [
                {
                  "affected_installed_packages": [
                    "libzstd"
                  ],
                  "name": "CVE-2021-24031",
                  "priority": "medium"
                },
                {
                  "affected_installed_packages": [
                    "libzstd"
                  ],
                  "name": "CVE-2021-24032",
                  "priority": "medium"
                }
              ],
              "related_launchpad_bugs": []
            }
          ],
          "vulnerability_data_published_at": ".*"
        },
        "meta": {
          "environment_vars": []
        },
        "type": "USNVulnerabilities"
      }
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
