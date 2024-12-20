Feature: LXD Pro features

  Scenario Outline: lxd_guest_attach setting
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro config show` with sudo
    Then stdout matches regexp:
      """
      lxd_guest_attach +off
      """
    Then I verify that no files exist matching `/var/lib/ubuntu-pro/interfaces/lxd-config.json`
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
    Then I verify that no files exist matching `/var/lib/ubuntu-pro/interfaces/lxd-config.json`
    When I run `pro config set lxd_guest_attach=available` with sudo
    When I run `pro config show` with sudo
    Then stdout matches regexp:
      """
      lxd_guest_attach +available
      """
    When I run `cat /var/lib/ubuntu-pro/interfaces/lxd-config.json` with sudo
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
    When I run `cat /var/lib/ubuntu-pro/interfaces/lxd-config.json` with sudo
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
    When I run `cat /var/lib/ubuntu-pro/interfaces/lxd-config.json` with sudo
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
    When I run `cat /var/lib/ubuntu-pro/interfaces/lxd-config.json` with sudo
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
    Then I verify that no files exist matching `/var/lib/ubuntu-pro/interfaces/lxd-config.json`
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

  Scenario Outline: LXD guest auto-attach behaves reasonably when lxd doesn't support it
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `lxd init --minimal` with sudo
    When I start `lxd-download` command `lxc image copy ubuntu-daily:noble local:` in the background
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    When I run `pro config show` with sudo
    Then stdout matches regexp:
      """
      lxd_guest_attach +off
      """
    When I wait for the `lxd-download` command to complete
    When I run `lxc launch ubuntu-daily:<guest_release> guest` with sudo
    When I install ubuntu-advantage-tools on the `guest` lxd guest
    Then I verify that running `lxc exec guest -- pro auto-attach` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      The running version of LXD does not support guest auto attach
      """
    When I run `pro config set lxd_guest_attach=available` with sudo
    Then I verify that running `lxc exec guest -- pro auto-attach` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      The running version of LXD does not support guest auto attach
      """
    When I run `pro config set lxd_guest_attach=on` with sudo
    When I run `lxc restart guest` with sudo
    # it may take some time for the nested guest to get networking
    When I wait `30` seconds
    When I run `lxc exec guest -- pro status --wait` with sudo
    When I run `lxc exec guest -- pro api u.pro.status.is_attached.v1` with sudo
    When I apply this jq filter `.attributes.is_attached` to the API data field output
    Then I will see the following on stdout:
      """
      false
      """
    When I run `lxc exec guest -- sh -c "journalctl -b -o cat -u ubuntu-advantage.service | grep '\['"` with sudo
    When I apply this jq filter `.[5] | select(. == "LXD instance API returned error for ubuntu-pro query")` to the output
    Then I will see the following on stdout:
      """
      "LXD instance API returned error for ubuntu-pro query"
      """
    Then I verify that running `lxc exec guest -- pro auto-attach` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      The running version of LXD does not support guest auto attach
      """

    Examples:
      | release | machine_type | guest_release |
      | jammy   | lxd-vm       | jammy         |

  Scenario Outline: LXD guest auto-attach
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    # Ensure default is "off" and setup lxd
    When I run `snap refresh lxd --channel latest/edge` with sudo
    When I run `lxd init --minimal` with sudo
    When I start `lxd-download` command `lxc image copy ubuntu-daily:noble local:` in the background
    When I run `pro config show` with sudo
    Then stdout matches regexp:
      """
      lxd_guest_attach +off
      """
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    When I run `pro config show` with sudo
    Then stdout matches regexp:
      """
      lxd_guest_attach +off
      """
    When I wait for the `lxd-download` command to complete
    When I run `lxc launch ubuntu-daily:<guest_release> guest` with sudo
    When I install ubuntu-advantage-tools on the `guest` lxd guest
    When I run `lxc exec guest -- cloud-init clean --machine-id --logs` with sudo
    When I run `lxc stop guest` with sudo
    When I run `lxc publish guest --alias protest` with sudo
    When I run `lxc delete guest` with sudo
    # Test "off" -> "available" -> "off"
    When I run `lxc launch protest guest` with sudo
    # This is a race with cloud-init, so wait a while
    When I wait `10` seconds
    Then I verify that running `lxc exec guest -- pro auto-attach` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      The LXD host does not allow guest auto attach
      """
    When I run `pro config set lxd_guest_attach=available` with sudo
    When I run `lxc exec guest -- pro auto-attach` with sudo
    When I run `lxc exec guest -- pro api u.pro.status.is_attached.v1` with sudo
    When I apply this jq filter `.attributes.is_attached` to the API data field output
    Then I will see the following on stdout:
      """
      true
      """
    When I run `lxc exec guest -- pro detach --assume-yes` with sudo
    When I run `pro config set lxd_guest_attach=off` with sudo
    Then I verify that running `lxc exec guest -- pro auto-attach` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      The LXD host does not allow guest auto attach
      """
    # Test "on" from launch and on restart
    When I run `lxc delete --force guest` with sudo
    When I run `pro config set lxd_guest_attach=on` with sudo
    When I run `lxc launch protest guest` with sudo
    # This is a race with cloud-init, so wait a while
    When I wait `30` seconds
    When I run `lxc exec guest -- pro status --wait` with sudo
    When I run `lxc exec guest -- pro api u.pro.status.is_attached.v1` with sudo
    When I apply this jq filter `.attributes.is_attached` to the API data field output
    Then I will see the following on stdout:
      """
      true
      """
    When I run `lxc exec guest -- pro detach --assume-yes` with sudo
    When I run `lxc restart guest` with sudo
    When I wait `30` seconds
    When I run `lxc exec guest -- pro status --wait` with sudo
    When I run `lxc exec guest -- pro api u.pro.status.is_attached.v1` with sudo
    When I apply this jq filter `.attributes.is_attached` to the API data field output
    Then I will see the following on stdout:
      """
      true
      """
    # Test "unset" (which should set to "off")
    When I run `pro config unset lxd_guest_attach` with sudo
    When I run `lxc exec guest -- pro detach --assume-yes` with sudo
    Then I verify that running `lxc exec guest -- pro auto-attach` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      The LXD host does not allow guest auto attach
      """

    Examples:
      | release | machine_type | guest_release |
      | jammy   | lxd-vm       | jammy         |
