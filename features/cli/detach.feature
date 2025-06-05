@uses.config.contract_token
Feature: CLI detach command

  Scenario Outline: Attached detach in an ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I verify that `Bearer ` field is redacted in the logs
    And I verify that `'attach', '` field is redacted in the logs
    And I verify that `'machineToken': '` field is redacted in the logs
    And I run `pro api u.pro.status.enabled_services.v1` as non-root
    Then API data field output is:
      """
      {
        "attributes": {
          "enabled_services": [
            {
              "name": "esm-apps",
              "variant_enabled": false,
              "variant_name": null
            },
            {
              "name": "esm-infra",
              "variant_enabled": false,
              "variant_name": null
            }
          ]
        },
        "meta": {
          "environment_vars": []
        },
        "type": "EnabledServices"
      }
      """
    Then I verify that running `pro detach` `as non-root` exits `1`
    And stderr matches regexp:
      """
      This command must be run as root \(try using sudo\).
      """
    When I run `pro detach --assume-yes` with sudo
    Then I will see the following on stdout:
      """
      Detach will disable the following services:
          esm-apps
          esm-infra
      Removing APT access to Ubuntu Pro: ESM Apps
      Updating package lists
      Removing APT access to Ubuntu Pro: ESM Infra
      Updating package lists
      This machine is now detached.
      """
    And the machine is unattached
    And I verify that no files exist matching `/etc/apt/auth.conf.d/90ubuntu-advantage`
    And I ensure apt update runs without errors
    When I attach `contract_token` with sudo
    And I verify that running `pro enable foobar --format json` `as non-root` exits `1`
    Then stdout is a json matching the `ua_operation` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [
          {
            "message": "json formatted response requires --assume-yes flag.",
            "message_code": "json-format-require-assume-yes",
            "service": null,
            "type": "system"
          }
        ],
        "failed_services": [],
        "needs_reboot": false,
        "processed_services": [],
        "result": "failure",
        "warnings": []
      }
      """
    Then I verify that running `pro enable foobar --format json` `with sudo` exits `1`
    And stdout is a json matching the `ua_operation` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [
          {
            "message": "json formatted response requires --assume-yes flag.",
            "message_code": "json-format-require-assume-yes",
            "service": null,
            "type": "system"
          }
        ],
        "failed_services": [],
        "needs_reboot": false,
        "processed_services": [],
        "result": "failure",
        "warnings": []
      }
      """
    Then I verify that running `pro detach --format json --assume-yes` `as non-root` exits `1`
    And stdout is a json matching the `ua_operation` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [
          {
            "message": "This command must be run as root (try using sudo).",
            "message_code": "nonroot-user",
            "service": null,
            "type": "system"
          }
        ],
        "failed_services": [],
        "needs_reboot": false,
        "processed_services": [],
        "result": "failure",
        "warnings": []
      }
      """
    When I run `pro detach --format json --assume-yes` with sudo
    Then stdout is a json matching the `ua_operation` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [],
        "failed_services": [],
        "needs_reboot": false,
        "processed_services": [
          "esm-apps",
          "esm-infra"
        ],
        "result": "success",
        "warnings": []
      }
      """
    And the machine is unattached

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | bionic  | wsl           |
      | focal   | lxd-container |
      | focal   | wsl           |
      | jammy   | lxd-container |
      | jammy   | wsl           |
      | noble   | lxd-container |

  Scenario Outline: Unattached detach command
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I verify that running `pro detach` `as non-root` exits `1`
    Then I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    When I verify that running `pro detach` `with sudo` exits `1`
    Then stderr matches regexp:
      """
      This machine is not attached to an Ubuntu Pro subscription.
      See https://ubuntu.com/pro
      """

    Examples: pro commands
      | release  | machine_type  |
      | bionic   | lxd-container |
      | bionic   | wsl           |
      | focal    | lxd-container |
      | focal    | wsl           |
      | xenial   | lxd-container |
      | jammy    | lxd-container |
      | jammy    | wsl           |
      | noble    | lxd-container |
      | oracular | lxd-container |
      | plucky   | lxd-container |
