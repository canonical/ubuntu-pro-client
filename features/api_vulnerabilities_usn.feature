Feature: Client behaviour for USN vulnerabilities API

  @uses.config.contract_token
  Scenario Outline: USN vulnerabilities for xenial machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    # Check we can download and parse the JSON data
    And I run `pro api u.pro.security.vulnerabilities.usn.v1` as non-root
    And I apt install `jq`
    And I push static file `security_issues_xenial.xz` to machine
    And I run `unxz -d /tmp/security_issues_xenial.xz` as non-root
    And I run shell command `pro api u.pro.security.vulnerabilities.usn.v1 --args data_file=/tmp/security_issues_xenial | jq '.data.attributes.usns[] | select (.name == \"USN-4976-2\")'` as non-root
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
          "CVE-2021-3448"
        \],
        "related_launchpad_bugs": \[\]
      }
      """
    When I apt install `dnsmasq-base`
    And I run shell command `pro api u.pro.security.vulnerabilities.usn.v1 --args data_file=/tmp/security_issues_xenial | jq .data.attributes.usns` as non-root
    Then stdout does not match regexp:
      """
      "name": "USN-4976-2",
      """
    When I run shell command `pro api u.pro.security.vulnerabilities.usn.v1 --data '{\"unfixable\": true, \"data_file\": \"/tmp/security_issues_xenial\"}'` as non-root
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
    When I create the file `/tmp/manifest` with the following:
      """
      libzstd1:amd634     1.3.1+dfsg-1~ubuntu0.16.04.1
      """
    And I run `pro api u.pro.security.vulnerabilities.usn.v1 --args data_file=/tmp/security_issues_xenial manifest_file=/tmp/manifest` as non-root
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "apt_updated_at": ".*",
          "usns": [
            {
              "affected_packages": [
                {
                  "current_version": ".*",
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
                "CVE-2019-11922"
              ],
              "related_launchpad_bugs": []
            },
            {
              "affected_packages": [
                {
                  "current_version": ".*",
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
                "CVE-2021-24031",
                "CVE-2021-24032"
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
