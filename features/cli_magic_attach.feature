Feature: CLI magic attach flow

  Scenario Outline: Attach using the magic attach flow
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/tmp/response-overlay.json` with the following:
      """
      {
          "https://contracts.canonical.com/v1/magic-attach": [
          {
            "code": 200,
            "response": {
              "userCode": "123",
              "token": "testToken",
              "expires": "expire-date",
              "expiresIn": 2000
            }
          },
          {
              "code": 200,
              "response": {
                  "userCode": "123",
                  "token": "testToken",
                  "expires": "expire-date",
                  "expiresIn": 2000,
                  "contractID": "test-contract-id",
                  "contractToken": "$behave_var{contract_token}"
              }
          }]
      }
      """
    And I append the following on uaclient config:
      """
      features:
        serviceclient_url_responses: "/tmp/response-overlay.json"
      """
    And I run `pro attach` with sudo
    Then stdout matches regexp:
      """
      Initiating attach operation...

      Please sign in to your Ubuntu Pro account at this link:
      https://ubuntu.com/pro/attach
      And provide the following code: .*123.*

      Attaching the machine...
      """
    And the machine is attached

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |
