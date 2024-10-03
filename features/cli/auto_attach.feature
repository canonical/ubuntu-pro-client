Feature: CLI auto-attach command

  @uses.config.contract_token
  Scenario Outline: Attached auto-attach in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then I verify that running `pro auto-attach` `as non-root` exits `1`
    And stderr matches regexp:
      """
      This command must be run as root \(try using sudo\).
      """
    When I verify that running `pro auto-attach` `with sudo` exits `2`
    Then stderr matches regexp:
      """
      This machine is already attached to '.+'
      To use a different subscription first run: sudo pro detach.
      """
    When I append the following on uaclient config:
      """
      features:
        disable_auto_attach: true
      """
    And I run `pro detach --assume-yes` with sudo
    Then I verify that running `pro auto-attach` `with sudo` exits `1`
    Then stderr matches regexp:
      """
      features.disable_auto_attach set in config
      """

    Examples: ubuntu release
      | release  | machine_type  |
      | xenial   | lxd-container |
      | bionic   | lxd-container |
      | focal    | lxd-container |
      | jammy    | lxd-container |
      | noble    | lxd-container |
      | oracular | lxd-container |

  @arm64
  Scenario Outline: Unattached auto-attach does nothing in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    # Fake a non-lxd cloud-id
    When I replace `"lxd"` in `/run/cloud-init/instance-data.json` with `"cloudy-cloud"`
    # Validate systemd unit/timer syntax
    When I run `systemd-analyze verify /lib/systemd/system/ua-timer.timer` with sudo
    Then stderr does not match regexp:
      """
      .*\/lib\/systemd/system\/ua.*
      """
    When I verify that running `pro auto-attach` `as non-root` exits `1`
    Then stderr matches regexp:
      """
      This command must be run as root \(try using sudo\).
      """
    When I run `pro auto-attach` with sudo
    Then stderr matches regexp:
      """
      Auto-attach image support is not available on cloudy-cloud
      See: https://canonical-ubuntu-pro-client.readthedocs-hosted.com/en/latest/explanations/what_are_ubuntu_pro_cloud_instances.html
      """

    Examples: ubuntu release
      | release  | machine_type  |
      | xenial   | lxd-container |
      | bionic   | lxd-container |
      | focal    | lxd-container |
      | jammy    | lxd-container |
      | noble    | lxd-container |
      | oracular | lxd-container |
