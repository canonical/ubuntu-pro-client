Feature: Attach API endpoint

  Scenario Outline: Attach API endpoint
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I verify that running `pro api u.pro.attach.token.full_token_attach.v1 --args token=TOKEN` `as non-root` exits `1`
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
    When I verify that running `pro api u.pro.attach.token.full_token_attach.v1 --args token=TOKEN` `with sudo` exits `1`
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
            "code": "attach-invalid-token",
            "meta": {},
            "title": "Invalid token. See https://ubuntu.com/pro/dashboard"
          }
        ],
        "result": "failure",
        "version": ".*",
        "warnings": []
      }
      """
    When I attach using the API
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `attach` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "v1",
        "data": {
          "attributes": {
            "enabled": [
              "esm-apps",
              "esm-infra"
            ],
            "reboot_required": false
          },
          "meta": {
            "environment_vars": []
          },
          "type": "FullTokenAttach"
        },
        "errors": [],
        "result": "success",
        "version": ".*",
        "warnings": []
      }
      """
    And the machine is attached
    And I verify that `esm-apps` is enabled
    And I verify that `esm-infra` is enabled
    When I run `pro detach --assume-yes` with sudo
    And I attach using the API without enabling services
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `attach` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "v1",
        "data": {
          "attributes": {
            "enabled": [],
            "reboot_required": false
          },
          "meta": {
            "environment_vars": []
          },
          "type": "FullTokenAttach"
        },
        "errors": [],
        "result": "success",
        "version": ".*",
        "warnings": []
      }
      """
    And the machine is attached
    And I verify that `esm-apps` is disabled
    And I verify that `esm-infra` is disabled

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
