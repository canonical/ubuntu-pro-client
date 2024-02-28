@uses.config.contract_token
Feature: Reboot Commands

  Scenario Outline: reboot-cmds removes fips package holds and updates packages
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    When I apt install `strongswan`
    When I run `pro enable fips --assume-yes` with sudo
    When I reboot the machine
    Then I verify that `fips` is enabled
    When I apt install `strongswan=<old_version>`
    When I run `apt-mark hold strongswan` with sudo
    When I run `dpkg-reconfigure ubuntu-advantage-tools` with sudo
    When I run `pro status` with sudo
    Then stdout matches regexp:
      """
      NOTICES
      Reboot to FIPS kernel required
      """
    When I reboot the machine
    And I verify that running `systemctl status ua-reboot-cmds.service` `as non-root` exits `0,3`
    Then stdout matches regexp:
      """
      .*status=0\/SUCCESS.*
      """
    When I run `pro status` with sudo
    Then stdout does not match regexp:
      """
      NOTICES
      """
    When I run `apt-mark showholds` with sudo
    Then I will see the following on stdout:
      """
      """
    When I run `apt policy strongswan` with sudo
    Then stdout contains substring:
      """
      *** <new_version> 1001
      """

    Examples: ubuntu release
      | release | machine_type  | old_version    | new_version               |
      | focal   | lxd-container | 5.8.2-1ubuntu3 | 5.8.2-1ubuntu3.fips.3.1.2 |
