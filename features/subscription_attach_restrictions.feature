@uses.config.contract_token
Feature: One time pro subscription related tests

  @arm64
  Scenario Outline: Attach fail if subscription is restricted to release
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/tmp/response-overlay.json` with the following:
      """
      {
          "https://contracts.canonical.com/v1/context/machines/token": [
          {
            "code": 200,
            "response": {
              "machineTokenInfo": {
                "contractInfo": {
                  "resourceEntitlements": [
                    {
                      "type": "support",
                      "affordances": {
                        "onlySeries": "<onlyseries>"
                      }
                    }
                  ]
                }
              }
            }
        }]
      }
      """
    And I append the following on uaclient config:
      """
      features:
        serviceclient_url_responses: "/tmp/response-overlay.json"
      """
    When I attempt to attach `contract_token` with sudo
    Then stderr contains substring:
      """
      Attaching to this contract is only allowed on the Ubuntu <onlyrelease> (<onlyseries_codename>) release
      """
    And the machine is unattached

    Examples: ubuntu release
      | release | machine_type  | onlyseries | onlyrelease | onlyseries_codename |
      | xenial  | lxd-container | bionic     | 18.04 LTS   | Bionic Beaver       |
      | bionic  | lxd-container | xenial     | 16.04 LTS   | Xenial Xerus        |
      | focal   | lxd-container | noble      | 24.04 LTS   | Noble Numbat        |
      | jammy   | lxd-container | focal      | 20.04 LTS   | Focal Fossa         |
      | noble   | lxd-container | jammy      | 22.04 LTS   | Jammy Jellyfish     |

  @arm64
  Scenario Outline: Check notice visible when attached with onlySeries present
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/tmp/response-overlay.json` with the following:
      """
      {
          "https://contracts.canonical.com/v1/context/machines/token": [
          {
            "code": 200,
            "response": {
              "machineTokenInfo": {
                "accountInfo": {
                  "name": "testName",
                  "id": "testAccID"
                },
                "contractInfo": {
                  "id": "testCID",
                  "name": "testName",
                  "resourceEntitlements": [
                    {
                      "type": "support",
                      "affordances": {
                        "onlySeries": "<onlyseries>"
                      }
                    }
                  ]
                },
                "machineId": "testMID"
              }
            }
        }],
        "https://contracts.canonical.com/v1/contracts/testCID/context/machines/testMID": [
          {
            "code": 200,
            "response": {
              "activityToken": "test-activity-token",
              "activityID": "test-activity-id",
              "activityPingInterval": 123456789
            }
          }],
          "https://contracts.canonical.com/v1/contracts/testCID/machine-activity/testMID": [
          {
            "code": 200,
            "response": {
              "activityToken": "test-activity-token",
              "activityID": "test-activity-id",
              "activityPingInterval": 123456789
            }
          }]
      }
      """
    And I append the following on uaclient config:
      """
      features:
        serviceclient_url_responses: "/tmp/response-overlay.json"
      """
    When I attach `contract_token` with sudo
    Then the machine is attached
    When I run `pro status` with sudo
    Then stdout contains substring:
      """
      Limited to release: Ubuntu <onlyrelease> (<onlyseries_codename>)
      """

    Examples: ubuntu release
      | release | machine_type  | onlyseries | onlyrelease | onlyseries_codename |
      | xenial  | lxd-container | xenial     | 16.04 LTS   | Xenial Xerus        |
      | bionic  | lxd-container | bionic     | 18.04 LTS   | Bionic Beaver       |
      | focal   | lxd-container | focal      | 20.04 LTS   | Focal Fossa         |
      | jammy   | lxd-container | jammy      | 22.04 LTS   | Jammy Jellyfish     |
      | noble   | lxd-container | noble      | 24.04 LTS   | Noble Numbat        |
