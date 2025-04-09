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
      Attaching to this contract is only allowed on the Ubuntu <onlyrelease> (<onlyseries_codename>) and previous releases.
      """
    And the machine is unattached

    Examples: ubuntu release
      | release | machine_type  | onlyseries | onlyrelease | onlyseries_codename |
      | xenial  | lxd-container | trusty     | 14.04 LTS   | Trusty Tahr         |
      | bionic  | lxd-container | xenial     | 16.04 LTS   | Xenial Xerus        |
      | focal   | lxd-container | bionic     | 18.04 LTS   | Bionic Beaver       |
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
      Limited to Ubuntu <onlyrelease> (<onlyseries_codename>) and previous releases
      """

    Examples: ubuntu release
      | release | machine_type  | onlyseries | onlyrelease | onlyseries_codename |
      | xenial  | lxd-container | xenial     | 16.04 LTS   | Xenial Xerus        |
      | xenial  | lxd-container | bionic     | 18.04 LTS   | Bionic Beaver       |
      | xenial  | lxd-container | noble      | 24.04 LTS   | Noble Numbat        |
      | bionic  | lxd-container | bionic     | 18.04 LTS   | Bionic Beaver       |
      | bionic  | lxd-container | focal      | 20.04 LTS   | Focal Fossa         |
      | focal   | lxd-container | focal      | 20.04 LTS   | Focal Fossa         |
      | focal   | lxd-container | jammy      | 22.04 LTS   | Jammy Jellyfish     |
      | jammy   | lxd-container | jammy      | 22.04 LTS   | Jammy Jellyfish     |
      | jammy   | lxd-container | noble      | 24.04 LTS   | Noble Numbat        |
      | noble   | lxd-container | noble      | 24.04 LTS   | Noble Numbat        |
