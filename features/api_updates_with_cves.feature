Feature: Client behaviour for updates with CVEs API

  @uses.config.contract_token
  Scenario Outline: Updates with CVEs for xenial machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I apt install `jq`
    And I push static file `security_issues_xenial.bz2` to machine
    And I run `bzip2 -d /tmp/security_issues_xenial.bz2` as non-root
    And I run shell command `pro api u.pro.packages.updates_with_cves.v1 --args data_file=/tmp/security_issues_xenial | jq '.data.attributes.updates[] | select (.package == \"bash\")'` as non-root
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
      }
      """
    When I run shell command `pro api u.pro.packages.updates_with_cves.v1 --args data_file=/tmp/security_issues_xenial | jq '.data.attributes.cves[] | select (.name == \"CVE-2019-18276\")'` as non-root
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
      }
      """
    When I apt install `bash`
    And I run `pro api u.pro.packages.updates_with_cves.v1 --args data_file=/tmp/security_issues_xenial` as non-root
    Then stdout does not contain substring:
      """
      "CVE-2019-18276",
      """
    When I create the file `/tmp/updates` with the following:
      """
      {
        "_schema_version": "v1",
        "data": {
          "attributes": {
            "summary": {
              "num_esm_apps_updates": 0,
              "num_esm_infra_updates": 1,
              "num_standard_security_updates": 0,
              "num_standard_updates": 0,
              "num_updates": 1
            },
            "updates": [
              {
                "download_size": 178816,
                "origin": "esm.ubuntu.com",
                "package": "busybox-initramfs",
                "provided_by": "esm-infra",
                "status": "pending_attach",
                "version": "1:1.22.0-15ubuntu1.4+esm2"
              }
            ]
          },
          "meta": {
            "environment_vars": []
          },
          "type": "PackageUpdates"
        },
        "errors": [],
        "result": "success",
        "version": "32.3",
        "warnings": []
      }
      """
    And I run `pro api u.pro.packages.updates_with_cves.v1 --args data_file=/tmp/security_issues_xenial updates_data=/tmp/updates` as non-root
    Then API data field output matches regexp
      """
      {
        "attributes": {
          "cves": [
            {
              "cvss_score": 7.5,
              "cvss_severity": "high",
              "description": ".*",
              "name": "CVE-2021-28831",
              "notes": [],
              "published_at": ".*",
              "ubuntu_priority": "low"
            },
            {
              "cvss_score": 9.8,
              "cvss_severity": "critical",
              "description": ".*",
              "name": "CVE-2022-48174",
              "notes": [
                ".*"
              ],
              "published_at": ".*",
              "ubuntu_priority": "low"
            }
          ],
          "summary": {
            "num_esm_apps_updates": 0,
            "num_esm_infra_updates": 1,
            "num_standard_security_updates": 0,
            "num_standard_updates": 0,
            "num_updates": 1
          },
          "updates": [
            {
              "download_size": 178816,
              "origin": "esm.ubuntu.com",
              "package": "busybox-initramfs",
              "provided_by": "esm-infra",
              "related_cves": [
                "CVE-2021-28831",
                "CVE-2022-48174"
              ],
              "status": "pending_attach",
              "version": "1:1.22.0\-15ubuntu1.4\+esm2"
            }
          ],
          "vulnerability_data_published_at": ".*"
        },
        "meta": {
          "environment_vars": []
        },
        "type": "PackageUpdatesWithCVE"
      }
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
