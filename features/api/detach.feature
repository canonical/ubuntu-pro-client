Feature: Detach API endpoint

  @uses.config.contract_token @arm64
  Scenario Outline: Detach API endpoint on an attached machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I verify that running `pro api u.pro.detach.v1` `as non-root` exits `1`
    Then stdout is a json matching the `api_response` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "v1",
        "data": {
          "meta": {
            "environment_vars": []
          }
        },
        "errors": [
          {
            "code": "nonroot-user",
            "meta": {},
            "title": "This command must be run as root (try using sudo)."
          }
        ],
        "result": "failure",
        "version": ".*",
        "warnings": []
      }
      """
    When I run `pro api u.pro.detach.v1` with sudo
    Then stdout is a json matching the `api_response` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "v1",
        "data": {
          "attributes": {
            "disabled": [],
            "reboot_required": false
          },
          "meta": {
            "environment_vars": []
          },
          "type": "Detach"
        },
        "errors": [],
        "result": "success",
        "version": ".*",
        "warnings": []
      }
      """
    When I attach `contract_token` with sudo
    And I run `pro api u.pro.detach.v1` with sudo
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `detach` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "v1",
        "data": {
          "attributes": {
            "disabled": [
              "esm-apps",
              "esm-infra"
            ],
            "reboot_required": false
          },
          "meta": {
            "environment_vars": []
          },
          "type": "Detach"
        },
        "errors": [],
        "result": "success",
        "version": ".*",
        "warnings": []
      }
      """
    When I attach `contract_token` with sudo
    And I run `touch /var/run/reboot-required` with sudo
    And I run `pro api u.pro.detach.v1` with sudo
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `detach` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "v1",
        "data": {
          "attributes": {
            "disabled": [
              "esm-apps",
              "esm-infra"
            ],
            "reboot_required": true
          },
          "meta": {
            "environment_vars": []
          },
          "type": "Detach"
        },
        "errors": [],
        "result": "success",
        "version": ".*",
        "warnings": []
      }
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
