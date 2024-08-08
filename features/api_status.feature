@uses.config.contract_token
Feature: Status behavior when using the api

  @uses.config.contract_token
  Scenario Outline: Subscription api when attached
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
          "machine_id": "TestMId"
        },
        "meta": {
          "environment_vars": []
        },
        "type": "subscription"
      }
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | mantic  | lxd-container |
      | noble   | lxd-container |

  Scenario Outline: Subscription api when unattached
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
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
            "effective": "",
            "expires": "",
            "id": "",
            "name": "",
            "origin": "",
            "products": [],
            "tech_support_level": ""
          },
          "machine_id": ""
        },
        "meta": {
          "environment_vars": []
        },
        "type": "subscription"
      }
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |

  Scenario Outline: u.pro.config.v1
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro api u.pro.config.v1` with sudo
    Then API data field output matches regexp:
      """
      \s*{
      \s*"attributes":\s*{
      \s*"apt_news":\s*true,
      \s*"apt_news_url":\s*"https://motd.ubuntu.com/aptnews.json",
      \s*"global_apt_http_proxy":\s*null,
      \s*"global_apt_https_proxy":\s*null,
      \s*"http_proxy":\s*null,
      \s*"https_proxy":\s*null,
      \s*"metering_timer":\s*14400,
      \s*"ua_apt_http_proxy":\s*null,
      \s*"ua_apt_https_proxy":\s*null,
      \s*"update_messaging_timer":\s*21600
      \s*},
      \s*"meta":\s*{
      \s*"environment_vars":\s*[]
      \s*},
      \s*"type":\s*"config"
      \s*}
      """
    When I append the following on uaclient config:
      """
      ua_config: {apt_news: false}
      """
    When I run `pro api u.pro.config.v1` with sudo
    Then API data field output matches regexp:
      """
      \s*{
      \s*"attributes":\s*{
      \s*"apt_news":\s*false,
      \s*"apt_news_url":\s*"https://motd.ubuntu.com/aptnews.json",
      \s*"global_apt_http_proxy":\s*null,
      \s*"global_apt_https_proxy":\s*null,
      \s*"http_proxy":\s*null,
      \s*"https_proxy":\s*null,
      \s*"metering_timer":\s*14400,
      \s*"ua_apt_http_proxy":\s*null,
      \s*"ua_apt_https_proxy":\s*null,
      \s*"update_messaging_timer":\s*21600
      \s*},
      \s*"meta":\s*{
      \s*"environment_vars":\s*[]
      \s*},
      \s*"type":\s*"config"
      \s*}
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |
