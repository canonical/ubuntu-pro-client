@uses.config.contract_token
Feature: Ensure network errors are handled gracefully across various services

  Scenario Outline: Various HTTP errors are handled gracefully on attaching contract token
    # This test simulates various HTTP errors by mocking the response from the serviceclient
    # when trying to attach contract token
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    # 400 Bad Request
    When I create a response overlay for `/v1/context/machines/token` with response code `400` and error message `Bad Request`
    And I append the following on uaclient config:
      """
      features:
        serviceclient_url_responses: "/tmp/response-overlay.json"
      """
    When I attempt to attach `contract_token` with sudo
    Then stderr contains substring:
      """
      Error connecting to /v1/context/machines/token: 400 {"error": "Bad Request"}
      """
    Then the machine is unattached
    # 404 Not Found
    When I create a response overlay for `/v1/context/machines/token` with response code `404` and error message `Not Found`
    And I append the following on uaclient config:
      """
      features:
        serviceclient_url_responses: "/tmp/response-overlay.json"
      """
    When I attempt to attach `contract_token` with sudo
    Then stderr contains substring:
      """
      Error connecting to /v1/context/machines/token: 404 {"error": "Not Found"}
      """
    Then the machine is unattached
    # 503 Bad Gateway
    When I create a response overlay for `/v1/context/machines/token` with response code `503` and error message `Bad Gateway`
    And I append the following on uaclient config:
      """
      features:
        serviceclient_url_responses: "/tmp/response-overlay.json"
      """
    When I attempt to attach `contract_token` with sudo
    Then stderr contains substring:
      """
      Error connecting to /v1/context/machines/token: 503 {"error": "Bad Gateway"}
      """
    Then the machine is unattached

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | noble   | lxd-container |

  Scenario Outline: Network errors for attaching contract token are handled gracefully
    # This test simulates network failure by disabling internet connection
    # and then trying to attach contract token
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I disable any internet connection on the machine
    And I attempt to attach `contract_token` with sudo
    Then stderr contains substring:
      """
      Failed to attach machine. See https://ubuntu.com/pro/dashboard
      """
    Then the machine is unattached

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | noble   | lxd-container |

  Scenario Outline: Network errors for enabling Realtime kernel and Livepatch are handled gracefully
    # This test simulates network failure by disabling internet connection
    # and then trying to enable realtime-kernel or livepatch
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    Then the machine is attached
    Then I verify that `<service>` is disabled
    When I disable any internet connection on the machine
    And I verify that running `pro enable <service> --assume-yes` `with sudo` exits `1`
    Then stderr contains substring:
      """
      Failed to connect to https://contracts.canonical.com/v1/contracts/
      """
    Then I verify that `<service>` is disabled

    # Realtime kernel is not supported on LXD containers so we must use a VM
    Examples: ubuntu release
      | release | machine_type  | service         |
      | xenial  | lxd-vm        | realtime-kernel |
      | noble   | lxd-vm        | realtime-kernel |
      | xenial  | lxd-container | livepatch       |
      | noble   | lxd-container | livepatch       |
