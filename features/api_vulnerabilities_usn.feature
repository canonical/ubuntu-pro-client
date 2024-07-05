Feature: Client behaviour for USN vulnerabilities API

  @uses.config.contract_token
  Scenario Outline: USN vulnerabilities for xenial machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    # Check we can download and parse the JSON data
    And I run `pro api u.pro.security.vulnerabilities.usn.v1` as non-root
    And I apt install `jq`
    And I push static file `security_issues_xenial.bz2` to machine
    And I run `bzip2 -d /tmp/security_issues_xenial.bz2` as non-root
    And I run shell command `pro api u.pro.security.vulnerabilities.usn.v1 --args data_file=/tmp/security_issues_xenial | jq .data.attributes.usns` as non-root
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

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
