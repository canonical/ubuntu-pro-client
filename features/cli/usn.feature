Feature: CLI usn command

  @uses.config.contract_token
  Scenario Outline: usn command on an attached machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I push static file `security_issues_jammy.json.xz` to machine
    And I create the file `/tmp/response-overlay.json` with the following:
      """
      {
        "https://security-metadata.canonical.com/oval/com.ubuntu.jammy.pkg.json.xz": [
          {
            "code": 200,
            "response": {
              "file_path": "/tmp/security_issues_jammy.json.xz"
            }
          }]
      }
      """
    And I append the following on uaclient config:
      """
      features:
        serviceclient_url_responses: "/tmp/response-overlay.json"
      """
    And I apt install `python3-urllib3`
    And I run `pro usn USN-7927-1` as non-root
    Then stdout matches regexp:
      """
      name:            USN-7927-1
      public-url:      https://ubuntu.com/security/notices/USN-7927-1
      title:           urllib3 vulnerabilities
      published-at:    2025-11-01
      updated-at:      2025-11-10
      superseded-by:   USN-7927-2
      priority:        .*high.*
      description: \|
        It was discovered that urllib3 incorrectly handled certain inputs. An attacker
        could possibly use this issue to bypass certain proxy restrictions.
      related_cves:
        - CVE-2025-66418
        - CVE-2025-66471
      affected_packages:
        python3-urllib3:  fixed  \(esm-infra\)  2.0.7-1ubuntu0.1
      """
    When I run `pro usn USN-7927-3` as non-root
    Then stdout matches regexp:
      """
      name:            USN-7927-3
      public-url:      https://ubuntu.com/security/notices/USN-7927-3
      title:           urllib3 regression
      published-at:    2025-11-10
      priority:        .*high.*
      description: \|
        USN-7927-2 introduced a regression in urllib3. This update fixes the problem.
      related_cves:
        - CVE-2025-66471
      affected_packages:
        python3-urllib3:  fixed  \(esm-infra\)  2.0.7-1ubuntu0.3
      """
    When I run `pro usn USN-9999-9` as non-root
    Then I will see the following on stderr:
      """
      USN-9999-9 doesn't affect Ubuntu 22.04.
      For more information, visit: https://ubuntu.com/security/notices/USN-9999-9
      """

    Examples: ubuntu release
      | release | machine_type  |
      | jammy   | lxd-container |
