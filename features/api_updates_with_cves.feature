Feature: Client behaviour for updates with CVEs API

  @uses.config.contract_token
  Scenario Outline: Updates with CVEs for xenial machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I apt install `jq`
    And I push static file `security_issues_xenial.bz2` to machine
    And I run `bzip2 -d /tmp/security_issues_xenial.bz2` as non-root
    And I run shell command `pro api u.pro.packages.updates_with_cves.v1 --args data_file=/tmp/security_issues_xenial | jq .data.attributes.updates` as non-root
    Then stdout matches regexp:
    """
      {
        "download_size": \d*,
        "origin": "esm.ubuntu.com",
        "package": "bash",
        "provided_by": "esm\-infra",
        "related_cves": \[
          "CVE\-2019\-18276"
        \],
        "status": "upgrade_available",
        "version": ".*"
      },
    """
    When I run shell command `pro api u.pro.packages.updates_with_cves.v1 --args data_file=/tmp/security_issues_xenial | jq .data.attributes.cves` as non-root
    Then stdout matches regexp:
    """
      {
        "cvss_score": 7.8,
        "cvss_severity": "high",
        "description": ".*",
        "name": "CVE-2019-18276",
        "notes": \[
          ".*"
        \],
        "published_at": ".*",
        "ubuntu_priority": "low"
      },
    """
    When I apt install `bash`
    And I run `pro api u.pro.packages.updates_with_cves.v1 --args data_file=/tmp/security_issues_xenial` as non-root
    Then stdout does not match regexp:
    """
    "CVE-2019-18276",
    """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
