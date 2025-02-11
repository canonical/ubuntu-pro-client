Feature: Subscription status api

  @uses.config.contract_token
  Scenario Outline: Subscription api when attached/unattached
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    When I set the machine token overlay to the following yaml:
      """
      machineTokenInfo:
        contractInfo:
          id: "TestCId"
          name: "TestCName"
          products: []
        accountInfo:
          id: "TestAAId"
          name: "TestAAName"
        machineId: "TestMId"
      """
    When I run `pro api u.pro.subscription.v1` with sudo
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "account": {
            "created_at": ".*",
            "external_account_ids": [],
            "id": "TestAAId",
            "name": "TestAAName"
          },
          "activity_id": ".*",
          "contract": {
            "created_at": ".*",
            "effective": null,
            "expires": ".*",
            "id": "TestCId",
            "name": "TestCName",
            "origin": null,
            "products": [],
            "tech_support_level": ".*"
          },
          "machine_id": "TestMId",
          "machine_is_attached": true
        },
        "meta": {
          "environment_vars": []
        },
        "type": "Subscription"
      }
      """
    When I run `pro detach --assume-yes` with sudo
    Then the machine is unattached
    When I run `pro api u.pro.subscription.v1` with sudo
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "account": {
            "created_at": "",
            "external_account_ids": [],
            "id": "",
            "name": ""
          },
          "activity_id": "",
          "contract": {
            "created_at": "",
            "effective": null,
            "expires": null,
            "id": "",
            "name": "",
            "origin": null,
            "products": [],
            "tech_support_level": null
          },
          "machine_id": "",
          "machine_is_attached": false
        },
        "meta": {
          "environment_vars": []
        },
        "type": "Subscription"
      }
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |
