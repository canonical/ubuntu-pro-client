Feature: Reboot required API endpoint

  @uses.config.contract_token
  Scenario Outline: Reboot required API working with livepatch
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then I verify that `livepatch` is enabled
    And I verify that `livepatch` status is warning
    When I run `pro api u.pro.security.status.reboot_required.v1` with sudo
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "livepatch_enabled": true,
          "livepatch_enabled_and_kernel_patched": true,
          "livepatch_state": "applied",
          "livepatch_support": "kernel-upgrade-required",
          "reboot_required": "no",
          "reboot_required_packages": {
            "kernel_packages": null,
            "standard_packages": null
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "RebootRequired"
      }
      """
    When I run `pro system reboot-required` as non-root
    Then I will see the following on stdout:
      """
      no
      """
    When I apt install `libc6`
    And I run `pro api u.pro.security.status.reboot_required.v1` as non-root
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "livepatch_enabled": true,
          "livepatch_enabled_and_kernel_patched": true,
          "livepatch_state": "applied",
          "livepatch_support": "kernel-upgrade-required",
          "reboot_required": "yes",
          "reboot_required_packages": {
            "kernel_packages": [],
            "standard_packages": [
              "libc6"
            ]
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "RebootRequired"
      }
      """
    When I run `pro system reboot-required` as non-root
    Then I will see the following on stdout:
      """
      yes
      """
    When I reboot the machine
    And I run `pro system reboot-required` as non-root
    Then I will see the following on stdout:
      """
      no
      """
    When I apt install `linux-image-generic`
    And I run `pro api u.pro.security.status.reboot_required.v1` as non-root
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "livepatch_enabled": true,
          "livepatch_enabled_and_kernel_patched": true,
          "livepatch_state": "applied",
          "livepatch_support": "kernel-upgrade-required",
          "reboot_required": "yes",
          "reboot_required_packages": {
            "kernel_packages": [
              "linux-base"
            ],
            "standard_packages": []
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "RebootRequired"
      }
      """
    When I run `pro system reboot-required` as non-root
    Then I will see the following on stdout:
      """
      yes
      """
    When I apt install `dbus`
    And I run `pro api u.pro.security.status.reboot_required.v1` with sudo
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "livepatch_enabled": true,
          "livepatch_enabled_and_kernel_patched": true,
          "livepatch_state": "applied",
          "livepatch_support": "kernel-upgrade-required",
          "reboot_required": "yes",
          "reboot_required_packages": {
            "kernel_packages": [
              "linux-base"
            ],
            "standard_packages": [
              "dbus"
            ]
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "RebootRequired"
      }
      """
    When I run `pro system reboot-required` as non-root
    Then I will see the following on stdout:
      """
      yes
      """

    Examples: ubuntu release
      | release | machine_type |
      | xenial  | lxd-vm       |
