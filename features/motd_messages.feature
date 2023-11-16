Feature: MOTD Messages

  @uses.config.contract_token
  Scenario Outline: Contract update prevents contract expiration messages
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    When I update contract to use `effectiveTo` as `$behave_var{today +2}`
    When I run `pro refresh messages` with sudo
    And I run `run-parts /etc/update-motd.d/` with sudo
    Then stdout does not match regexp:
      """
      [\w\d.]+

      CAUTION: Your Ubuntu Pro subscription will expire in 2 days.
      Renew your subscription at https:\/\/ubuntu.com\/pro\/dashboard to ensure
      continued security coverage for your applications.

      [\w\d.]+
      """
    When I update contract to use `effectiveTo` as `$behave_var{today -3}`
    When I run `pro refresh messages` with sudo
    And I run `run-parts /etc/update-motd.d/` with sudo
    Then stdout does not match regexp:
      """
      [\w\d.]+

      CAUTION: Your Ubuntu Pro subscription expired on \d+ \w+ \d+.
      Renew your subscription at https:\/\/ubuntu.com\/pro\/dashboard to ensure
      continued security coverage for your applications.
      Your grace period will expire in 11 days.

      [\w\d.]+
      """
    When I update contract to use `effectiveTo` as `$behave_var{today -20}`
    When I run `pro refresh messages` with sudo
    And I run `run-parts /etc/update-motd.d/` with sudo
    Then stdout does not match regexp:
      """
      [\w\d.]+

      \*Your Ubuntu Pro subscription has EXPIRED\*
      \d+ additional security updates require Ubuntu Pro with '<service>' enabled.
      Renew your subscription at https:\/\/ubuntu.com\/pro\/dashboard

      [\w\d.]+
      """

    Examples: ubuntu release
      | release | machine_type  | service   |
      | xenial  | lxd-container | esm-infra |
      | bionic  | lxd-container | esm-apps  |
      | bionic  | wsl           | esm-apps  |
      | noble   | lxd-container | esm-apps  |

  Scenario Outline: Contract Expiration Messages
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I apt install `ansible hello`
    And I attach `contract_token` with sudo
    And I set the machine token overlay to the following yaml
      """
      machineTokenInfo:
        contractInfo:
          effectiveTo: $behave_var{today +2}
      """
    And I run `pro refresh messages` with sudo
    And I run `run-parts /etc/update-motd.d/` with sudo
    Then stdout matches regexp:
      """
      [\w\d.]+

      CAUTION: Your Ubuntu Pro subscription will expire in 2 days.
      Renew your subscription at https:\/\/ubuntu.com\/pro\/dashboard to ensure
      continued security coverage for your applications.
      """
    When I set the machine token overlay to the following yaml
      """
      machineTokenInfo:
        contractInfo:
          effectiveTo: $behave_var{today -3}
      """
    When I run `pro refresh messages` with sudo
    And I run `run-parts /etc/update-motd.d/` with sudo
    Then stdout matches regexp:
      """
      [\w\d.]+

      CAUTION: Your Ubuntu Pro subscription expired on \d+ \w+ \d+.
      Renew your subscription at https:\/\/ubuntu.com\/pro\/dashboard to ensure
      continued security coverage for your applications.
      Your grace period will expire in 11 days.
      """
    When I set the machine token overlay to the following yaml
      """
      machineTokenInfo:
        contractInfo:
          effectiveTo: $behave_var{today -20}
      """
    When I run `pro refresh messages` with sudo
    And I run `run-parts /etc/update-motd.d/` with sudo
    Then stdout matches regexp:
      """
      [\w\d.]+

      \*Your Ubuntu Pro subscription has EXPIRED\*
      \d+ additional security update(s)? require(s)? Ubuntu Pro with '<service>' enabled.
      Renew your subscription at https:\/\/ubuntu.com\/pro\/dashboard
      """
    When I apt upgrade
    When I run `pro refresh messages` with sudo
    And I run `run-parts /etc/update-motd.d/` with sudo
    Then stdout matches regexp:
      """
      [\w\d.]+

      \*Your Ubuntu Pro subscription has EXPIRED\*
      Renew your subscription at https:\/\/ubuntu.com\/pro\/dashboard
      """
    When I create the file `/var/lib/ubuntu-advantage/machine-token-overlay.json` with the following:
      """
      {
          "machineTokenInfo": {
              "contractInfo": {
                  "effectiveTo": null
              }
          }
      }
      """
    When I wait `1` seconds
    When I run `pro refresh messages` with sudo
    And I run `run-parts /etc/update-motd.d/` with sudo
    Then stdout matches regexp:
      """
      [\w\d.]+

      \*Your Ubuntu Pro subscription has EXPIRED\*
      Renew your subscription at https:\/\/ubuntu.com\/pro\/dashboard
      """

    Examples: ubuntu release
      | release | machine_type  | service   |
      | xenial  | lxd-container | esm-infra |
      | bionic  | lxd-container | esm-infra |
      | bionic  | wsl           | esm-infra |
