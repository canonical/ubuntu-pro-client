Feature: ESM Resource Specificities

  Scenario Outline: enable esm in a machine with -updates disabled
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    And I run `sed -i '/<release>-updates/d' /etc/apt/sources.list` with sudo
    And I apt update
    And I run `pro enable esm-infra` with sudo
    And I run `pro enable esm-apps` with sudo
    And I run `cat /etc/apt/sources.list.d/ubuntu-esm-apps.list` with sudo
    Then stdout contains substring:
      """
      deb https://esm.ubuntu.com/apps/ubuntu <release>-apps-security main
      """
    And stdout contains substring:
      """
      # deb https://esm.ubuntu.com/apps/ubuntu <release>-apps-updates main
      """
    When I run `cat /etc/apt/sources.list.d/ubuntu-esm-infra.list` with sudo
    Then stdout contains substring:
      """
      deb https://esm.ubuntu.com/infra/ubuntu <release>-infra-security main
      """
    And stdout contains substring:
      """
      # deb https://esm.ubuntu.com/infra/ubuntu <release>-infra-updates main
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |

  Scenario Outline: enable esm in a machine with -updates disabled
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    And I replace `<release>-updates` in `/etc/apt/sources.list.d/ubuntu.sources` with ` `
    And I apt update
    And I run `pro enable esm-infra` with sudo
    And I run `pro enable esm-apps` with sudo
    And I run `cat /etc/apt/sources.list.d/ubuntu-esm-apps.sources` with sudo
    Then stdout contains substring:
      """
      <release>-apps-security
      """
    And stdout does not contain substring:
      """
      <release>-apps-updates
      """
    When I run `cat /etc/apt/sources.list.d/ubuntu-esm-infra.sources` with sudo
    Then stdout contains substring:
      """
      <release>-infra-security
      """
    And stdout does not contain substring:
      """
      <release>-infra-updates
      """

    Examples: ubuntu release
      | release | machine_type  |
      | noble   | lxd-container |

  Scenario Outline: esm apt auth includes snapshot urls
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    When I run `pro enable esm-infra esm-apps` with sudo
    When I run `cat /etc/apt/auth.conf.d/90ubuntu-advantage` with sudo
    Then stdout contains substring:
      """
      machine esm.ubuntu.com/infra/ubuntu/ login bearer password m
      """
    Then stdout contains substring:
      """
      machine snapshot.infra-security.esm.ubuntu.com/infra/ubuntu/ login bearer password m
      """
    Then stdout contains substring:
      """
      machine snapshot.infra-updates.esm.ubuntu.com/infra/ubuntu/ login bearer password m
      """
    Then stdout contains substring:
      """
      machine esm.ubuntu.com/apps/ubuntu/ login bearer password m
      """
    Then stdout contains substring:
      """
      machine snapshot.apps-security.esm.ubuntu.com/apps/ubuntu/ login bearer password m
      """
    Then stdout contains substring:
      """
      machine snapshot.apps-updates.esm.ubuntu.com/apps/ubuntu/ login bearer password m
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |
