Feature: Client behaviour for updates with CVEs API

  Scenario Outline: Updates with CVEs for xenial machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I apt update
    And I apt install `jq`
    And I run `python3 /usr/lib/ubuntu-advantage/esm_cache.py` with sudo
    And I run `sleep 10` as non-root
    And I run shell command `pro api u.pro.packages.updates_with_cves.v1 | jq .data.attributes.updates` as non-root
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
        "status": "pending_attach",
        "version": ".*"
      },
    """
    When I run shell command `pro api u.pro.packages.updates_with_cves.v1 | jq .data.attributes.cves` as non-root
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

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
