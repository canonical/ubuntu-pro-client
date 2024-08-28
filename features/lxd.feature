Feature: LXD Pro features

  Scenario Outline: lxd_guest_attach setting
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro config show` with sudo
    Then stdout matches regexp:
      """
      lxd_guest_attach +off
      """
    Then I verify that no files exist matching `/var/lib/ubuntu-advantage/interfaces/lxd-config.json`
    Then I verify that running `pro config set lxd_guest_attach=available` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      This machine is not attached to an Ubuntu Pro subscription.
      See https://ubuntu.com/pro
      """
    Then I verify that running `pro config set lxd_guest_attach=available` `as non-root` exits `1`
    Then I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    When I run `pro config show` with sudo
    Then stdout matches regexp:
      """
      lxd_guest_attach +off
      """
    Then I verify that no files exist matching `/var/lib/ubuntu-advantage/interfaces/lxd-config.json`
    When I run `pro config set lxd_guest_attach=available` with sudo
    When I run `pro config show` with sudo
    Then stdout matches regexp:
      """
      lxd_guest_attach +available
      """
    When I run `cat /var/lib/ubuntu-advantage/interfaces/lxd-config.json` with sudo
    When I apply this jq filter `.guest_attach` to the output
    Then I will see the following on stdout:
      """
      "available"
      """
    When I run `pro config set lxd_guest_attach=off` with sudo
    When I run `pro config show` with sudo
    Then stdout matches regexp:
      """
      lxd_guest_attach +off
      """
    When I run `cat /var/lib/ubuntu-advantage/interfaces/lxd-config.json` with sudo
    When I apply this jq filter `.guest_attach` to the output
    Then I will see the following on stdout:
      """
      "off"
      """
    When I run `pro config set lxd_guest_attach=on` with sudo
    When I run `pro config show` with sudo
    Then stdout matches regexp:
      """
      lxd_guest_attach +on
      """
    When I run `cat /var/lib/ubuntu-advantage/interfaces/lxd-config.json` with sudo
    When I apply this jq filter `.guest_attach` to the output
    Then I will see the following on stdout:
      """
      "on"
      """
    When I run `pro config unset lxd_guest_attach` with sudo
    When I run `pro config show` with sudo
    Then stdout matches regexp:
      """
      lxd_guest_attach +off
      """
    When I run `cat /var/lib/ubuntu-advantage/interfaces/lxd-config.json` with sudo
    When I apply this jq filter `.guest_attach` to the output
    Then I will see the following on stdout:
      """
      "off"
      """
    Then I verify that running `pro config set lxd_guest_attach=somethingelse` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      Value provided was not found in LXDGuestAttachEnum's allowed: value: ['on', 'off', 'available']
      """
    When I run `pro detach --assume-yes` with sudo
    Then I verify that no files exist matching `/var/lib/ubuntu-advantage/interfaces/lxd-config.json`
    When I create the file `/var/lib/ubuntu-advantage/private/user-config.json` with the following
      """
      {"lxd_guest_attach": "on"}
      """
    When I run `pro refresh config` with sudo
    Then I will see the following on stdout:
      """
      Warning: lxd_guest_attach is set to "on" or "available", but the machine is
      not attached. Ignoring.
      Successfully processed your pro configuration.
      """

    Examples:
      | release | machine_type  |
      | xenial  | lxd-container |
      | noble   | lxd-container |
