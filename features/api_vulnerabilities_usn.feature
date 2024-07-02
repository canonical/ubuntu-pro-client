Feature: Client behaviour for USN vulnerabilities API

  Scenario Outline: USN vulnerabilities for xenial machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I apt update
    And I apt install `jq`
    And I run shell command `pro api u.pro.security.vulnerabilities.usn.v1 | jq .data.attributes.usns` as non-root
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
      },
    """
    When I run shell command `pro api u.pro.security.vulnerabilities.usn.v1 --data '{\"all\": true}' | jq .data.attributes.usns` as non-root
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
      },
    """
    When I run shell command `pro api u.pro.security.vulnerabilities.usn.v1 --data '{\"unfixable\": true}'` as non-root
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

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
