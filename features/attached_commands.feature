@uses.config.contract_token
Feature: Command behaviour when attached to an Ubuntu Pro subscription

  Scenario Outline: Attached enable when reboot required
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I run `pro disable esm-infra` with sudo
    And I run `touch /var/run/reboot-required` with sudo
    And I run `touch /var/run/reboot-required.pkgs` with sudo
    And I run `pro enable esm-infra` with sudo
    Then stdout matches regexp:
      """
      Updating Ubuntu Pro: ESM Infra package lists
      Ubuntu Pro: ESM Infra enabled
      """
    And stdout does not match regexp:
      """
      A reboot is required to complete install.
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |

  Scenario Outline: Run timer script to valid machine activity endpoint
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I run `rm /var/lib/ubuntu-advantage/machine-token.json` with sudo
    Then the machine is unattached
    When I run `dpkg-reconfigure ubuntu-advantage-tools` with sudo
    Then I verify that files exist matching `/var/lib/ubuntu-advantage/machine-token.json`
    Then the machine is attached

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
