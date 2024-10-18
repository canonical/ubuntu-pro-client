Feature: Status notices api

  @uses.config.contract_token
  Scenario Outline: Check notices returned by status api
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
                        "onlySeries": "<only_series>"
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
    When I run `pro api u.pro.status.notices.v1` as non-root
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "notices": [
            {
              "label": "contract_expired",
              "message": ".*",
              "order_id": "5"
            },
            {
              "label": "limited_to_release",
              "message": ".*",
              "order_id": "80"
            }
          ]
        },
        "meta": {
          "environment_vars": []
        },
        "type": "NoticeList"
      }
      """

    Examples: ubuntu release
      | release  | machine_type  | only_series |
      | xenial   | lxd-container | xenial      |
      | bionic   | lxd-container | bionic      |
      | focal    | lxd-container | focal       |
      | jammy    | lxd-container | jammy       |
      | noble    | lxd-container | noble       |
      | oracular | lxd-container | oracular    |
