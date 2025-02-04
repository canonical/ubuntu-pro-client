Feature: CLI cve command

  @uses.config.contract_token
  Scenario Outline: cve command on an attached machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    # Check we can download and parse the JSON data
    And I run `pro cve CVE-2023-3297` as non-root
    And I push static file `security_issues_xenial.json.xz` to machine
    And I create the file `/tmp/response-overlay.json` with the following:
      """
      {
        "https://security-metadata.canonical.com/oval/com.ubuntu.xenial.pkg.json.xz": [
          {
            "code": 200,
            "response": {
              "file_path": "/tmp/security_issues_xenial.json.xz"
            }
          }]
      }
      """
    And I append the following on uaclient config:
      """
      features:
        serviceclient_url_responses: "/tmp/response-overlay.json"
      """
    And I run `pro cve CVE-2023-3297` as non-root
    Then stdout matches regexp:
      """
      name:            CVE-2023-3297
      public-url:      https://ubuntu.com/security/CVE-2023-3297
      published-at:    2023-06-28
      cve-cache-date:  2024-09-23
      apt-cache-date:  .*
      priority:        .*medium.*
      cvss-score:      8.1
      cvss-severity:   high
      description: \|
        In Ubuntu's accountsservice an unprivileged local attacker can trigger a
        use-after-free vulnerability in accountsservice by sending a D-Bus message to
        the accounts-daemon process.
      notes:
        - mdeslaur> This is GHSL-2023-139 Issue is in the Ubuntu-specific
          0010-set-language.patch patch.
        - eslerm\> CWE-416
      affected_packages:
        accountsservice:      fixed  \(esm-infra\)  0.6.40-2ubuntu11.6\+esm1
        libaccountsservice0:  fixed  \(esm-infra\)  0.6.40-2ubuntu11.6\+esm1
      related_usns:
        USN-6190-2: AccountsService vulnerability
      """
    When I apt install `accountsservice libaccountsservice0`
    And I run `pro cve CVE-2023-3297` as non-root
    Then stdout matches regexp:
      """
      name:            CVE-2023-3297
      public-url:      https://ubuntu.com/security/CVE-2023-3297
      published-at:    2023-06-28
      cve-cache-date:  2024-09-23
      apt-cache-date:  .*
      priority:        .*medium.*
      cvss-score:      8.1
      cvss-severity:   high
      description: \|
        In Ubuntu's accountsservice an unprivileged local attacker can trigger a
        use-after-free vulnerability in accountsservice by sending a D-Bus message to
        the accounts-daemon process.
      notes:
        - mdeslaur> This is GHSL-2023-139 Issue is in the Ubuntu-specific
          0010-set-language.patch patch.
        - eslerm\> CWE-416
      affected_packages: \[\]
      """
    When I run `pro cve CVE-2012-6655` as non-root
    Then stdout matches regexp:
      """
      name:            CVE-2012-6655
      public-url:      https://ubuntu.com/security/CVE-2012-6655
      published-at:    2019-11-27
      cve-cache-date:  2024-09-23
      apt-cache-date:  .*
      priority:        .*low.*
      cvss-score:      3.3
      cvss-severity:   low
      description: |
        An issue exists AccountService 0.6.37 in the
        user_change_password_authorized_cb\(\) function in user.c which could let a
        local users obtain encrypted passwords.
      affected_packages:
        accountsservice:      vulnerable
        libaccountsservice0:  vulnerable
      """
    When I run `pro cve CVE-2025-26520` as non-root
    Then I will see the following on stdout:
      """
      CVE-2025-26520 not present in xenial security data.
      You may be able to find more information at:
      - https://ubuntu.com/security/CVE-2025-26520
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
