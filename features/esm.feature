Feature: ESM Resource Specificities

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

  @oneoff
  Scenario Outline: attached upgrade to v35 adds snapshot urls for esm
    Given a `<release>` `<machine_type>` machine
    When I apt update
    When I apt upgrade
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    When I run `pro enable esm-infra esm-apps` with sudo
    When I run `cat /etc/apt/auth.conf.d/90ubuntu-advantage` with sudo
    Then stdout contains substring:
      """
      machine esm.ubuntu.com/infra/ubuntu/ login bearer password m
      """
    Then stdout does not contain substring:
      """
      machine snapshot.infra-security.esm.ubuntu.com/infra/ubuntu/ login bearer password m
      """
    Then stdout does not contain substring:
      """
      machine snapshot.infra-updates.esm.ubuntu.com/infra/ubuntu/ login bearer password m
      """
    Then stdout contains substring:
      """
      machine esm.ubuntu.com/apps/ubuntu/ login bearer password m
      """
    Then stdout does not contain substring:
      """
      machine snapshot.apps-security.esm.ubuntu.com/apps/ubuntu/ login bearer password m
      """
    Then stdout does not contain substring:
      """
      machine snapshot.apps-updates.esm.ubuntu.com/apps/ubuntu/ login bearer password m
      """
    When I install ubuntu-advantage-tools
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
