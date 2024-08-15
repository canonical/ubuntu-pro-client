Feature: CLI refresh command

  @uses.config.contract_token
  Scenario Outline: Attached refresh in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I verify that `Bearer ` field is redacted in the logs
    And I verify that `'attach', '` field is redacted in the logs
    And I verify that `'machineToken': '` field is redacted in the logs
    Then I verify that running `pro refresh` `as non-root` exits `1`
    And stderr matches regexp:
      """
      This command must be run as root \(try using sudo\).
      """
    When I run `pro refresh` with sudo
    Then I will see the following on stdout:
      """
      Successfully processed your pro configuration.
      Successfully refreshed your subscription.
      Successfully updated Ubuntu Pro related APT and MOTD messages.
      """
    When I run `pro refresh config` with sudo
    Then I will see the following on stdout:
      """
      Successfully processed your pro configuration.
      """
    When I run `pro refresh contract` with sudo
    Then I will see the following on stdout:
      """
      Successfully refreshed your subscription.
      """
    When I run `pro refresh messages` with sudo
    Then I will see the following on stdout:
      """
      Successfully updated Ubuntu Pro related APT and MOTD messages.
      """

    Examples: ubuntu release
      | release | machine_type  |
      | bionic  | lxd-container |
      | bionic  | wsl           |
      | focal   | lxd-container |
      | focal   | wsl           |
      | xenial  | lxd-container |
      | jammy   | lxd-container |
      | jammy   | wsl           |
      | mantic  | lxd-container |
      | noble   | lxd-container |

  Scenario Outline: Unattached commands that requires enabled user in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I verify that running `pro refresh` `as non-root` exits `1`
    Then I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    When I verify that running `pro refresh` `with sudo` exits `1`
    Then stderr matches regexp:
      """
      This machine is not attached to an Ubuntu Pro subscription.
      See https://ubuntu.com/pro
      """

    Examples: pro commands
      | release | machine_type  |
      | bionic  | lxd-container |
      | bionic  | wsl           |
      | focal   | lxd-container |
      | focal   | wsl           |
      | xenial  | lxd-container |
      | jammy   | lxd-container |
      | jammy   | wsl           |
      | mantic  | lxd-container |
      | noble   | lxd-container |
