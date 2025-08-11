@uses.config.contract_token
Feature: Enable cc-eal on Ubuntu

  @arm64
  Scenario Outline: Attached enable Common Criteria service in an ubuntu lxd container
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then I verify that running `pro enable cc-eal` `as non-root` exits `1`
    And I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    When I run `pro enable cc-eal` with sudo
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Configuring APT access to CC EAL2
      Updating CC EAL2 package lists
      (This will download more than 500MB of packages, so may take some time.)
      Updating standard Ubuntu package lists
      Installing CC EAL2 packages
      CC EAL2 enabled
      Please follow instructions in /usr/share/doc/ubuntu-commoncriteria/README to configure EAL2
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |

  @arm64
  Scenario Outline: Enable cc-eal with --access-only
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    When I run `pro enable cc-eal --access-only` with sudo
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Configuring APT access to CC EAL2
      Updating CC EAL2 package lists
      Skipping installing packages: ubuntu-commoncriteria
      CC EAL2 access enabled
      """
    Then I verify that running `apt-get install ubuntu-commoncriteria` `with sudo` exits `0`

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |

  Scenario Outline: Attached enable Common Criteria service in an ubuntu lxd container
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then I verify that running `pro enable cc-eal` `as non-root` exits `1`
    And I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    When I verify that running `pro enable cc-eal` `with sudo` exits `1`
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      CC EAL2 is not available for Ubuntu <version> (<full_name>).
      Could not enable CC EAL2.
      """

    Examples: ubuntu release
      | release  | machine_type  | version   | full_name       |
      | focal    | lxd-container | 20.04 LTS | Focal Fossa     |
      | jammy    | lxd-container | 22.04 LTS | Jammy Jellyfish |
      | noble    | lxd-container | 24.04 LTS | Noble Numbat    |
      | oracular | lxd-container | 24.10     | Oracular Oriole |
      | plucky   | lxd-container | 25.04     | Plucky Puffin   |
