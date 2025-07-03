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
      cve-cache-date:  .*
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
      cve-cache-date:  .*
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
      cve-cache-date:  .*
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
    Then I will see the following on stderr:
      """
      CVE-2025-26520 doesn't affect Ubuntu 16.04.
      For more information, visit: https://ubuntu.com/security/CVE-2025-26520
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |

  @uses.config.contract_token
  Scenario Outline: cve command for a kernel CVE
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I push static file `security_issues_focal.json.xz` to machine
    And I create the file `/tmp/response-overlay.json` with the following:
      """
      {
        "https://security-metadata.canonical.com/oval/com.ubuntu.focal.pkg.json.xz": [
          {
            "code": 200,
            "response": {
              "file_path": "/tmp/security_issues_focal.json.xz"
            }
          }]
      }
      """
    And I append the following on uaclient config:
      """
      features:
        serviceclient_url_responses: "/tmp/response-overlay.json"
      """
    And I run `pro cve CVE-2023-20569` as non-root
    Then stdout matches regexp:
      """
      name:            CVE-2023-20569
      public-url:      https://ubuntu.com/security/CVE-2023-20569
      published-at:    2023-08-08
      cve-cache-date:  .*
      apt-cache-date:  .*
      priority:        .*high.*
      cvss-score:      4.7
      cvss-severity:   medium
      description: |
        A side channel vulnerability on some of the AMD CPUs may allow an attacker to
        influence the return address prediction. This may result in speculative
        execution at an attacker-controlled address, potentially leading to
        information disclosure.
      notes:
        - alexmurray> The listed microcode revisions for 3rd Gen AMD EPYC processors
          in AMD-SB-7005 were provided to the upstream linux-firmware repo in commit
          b250b32ab1d044953af2dc5e790819a7703b7ee6 whilst the 4th Gen microcode was
          provided in commit f2eb058afc57348cde66852272d6bf11da1eef8f. This is not
          planned to be fixed for the amd64-microcode package in Ubuntu 14.04 as that
          release was already outside of the LTS timeframe when this hardware platform
          was launched.
        - ijwhitfield> Backports for 5.4 and earlier kernels are not planned due to a
          large number of dependency commits and having already backported patches to
          the AMD microcode package.
      affected_packages:
        linux-headers-5.4.0-1131-kvm:  vulnerable
        linux-kvm-headers-5.4.0-1131:  vulnerable
        linux-modules-5.4.0-1131-kvm:  vulnerable
      """

    Examples: ubuntu release
      | release | machine_type |
      | focal   | lxd-vm       |

  @uses.config.contract_token
  Scenario Outline: Cves command when vulnerability data doesn't exist
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `sed -i 's/^\(VERSION_CODENAME=\).*/\1invalid/' /etc/os-release` with sudo
    Then I verify that running `pro cve CVE-2023-3297` `as non-root` exits `1`
    Then I will see the following on stderr:
      """
      Vulnerability data not found for the current Ubuntu release
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
