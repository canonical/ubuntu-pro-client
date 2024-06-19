Feature: Config status api

  Scenario Outline: u.pro.config.v1
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro api u.pro.config.v1` with sudo
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "apt_news": true,
          "apt_news_url": "https://motd.ubuntu.com/aptnews.json",
          "cli_color": true,
          "cli_suggestions": true,
          "global_apt_http_proxy": null,
          "global_apt_https_proxy": null,
          "http_proxy": null,
          "https_proxy": null,
          "metering_timer": 14400,
          "ua_apt_http_proxy": null,
          "ua_apt_https_proxy": null,
          "update_messaging_timer": 21600,
          "vulnerability_data_url_prefix": "https://security-metadata.canonical.com/oval/"
        },
        "meta": {
          "environment_vars": []
        },
        "type": "Config"
      }
      """
    When I run `pro config set apt_news=false` with sudo
    When I run `pro api u.pro.config.v1` with sudo
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "apt_news": false,
          "apt_news_url": "https://motd.ubuntu.com/aptnews.json",
          "cli_color": true,
          "cli_suggestions": true,
          "global_apt_http_proxy": null,
          "global_apt_https_proxy": null,
          "http_proxy": null,
          "https_proxy": null,
          "metering_timer": 14400,
          "ua_apt_http_proxy": null,
          "ua_apt_https_proxy": null,
          "update_messaging_timer": 21600,
          "vulnerability_data_url_prefix": "https://security-metadata.canonical.com/oval/"
        },
        "meta": {
          "environment_vars": []
        },
        "type": "Config"
      }
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |

  Scenario Outline: Check proxy settings as sudo/non-root
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    Given a `focal` `lxd-container` machine named `proxy`
    When I apt install `squid` on the `proxy` machine
    And I add this text on `/etc/squid/squid.conf` on `proxy` above `http_access deny all`:
      """
      dns_v4_first on\nacl all src 0.0.0.0\/0\nhttp_access allow all
      """
    And I run `systemctl restart squid.service` `with sudo` on the `proxy` machine
    And I run `pro config set http_proxy=http://someuser:somepassword@$behave_var{machine-ip proxy}:3128` with sudo
    When I run `pro api u.pro.config.v1` with sudo
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "apt_news": true,
          "apt_news_url": "https://motd.ubuntu.com/aptnews.json",
          "cli_color": true,
          "cli_suggestions": true,
          "global_apt_http_proxy": null,
          "global_apt_https_proxy": null,
          "http_proxy": "http://someuser:somepassword@$behave_var{machine-ip proxy}:3128",
          "https_proxy": null,
          "metering_timer": 14400,
          "ua_apt_http_proxy": null,
          "ua_apt_https_proxy": null,
          "update_messaging_timer": 21600,
          "vulnerability_data_url_prefix": "https://security-metadata.canonical.com/oval/"
        },
        "meta": {
          "environment_vars": []
        },
        "type": "Config"
      }
      """
    When I run `pro api u.pro.config.v1` as non-root
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "apt_news": true,
          "apt_news_url": "https://motd.ubuntu.com/aptnews.json",
          "cli_color": true,
          "cli_suggestions": true,
          "global_apt_http_proxy": null,
          "global_apt_https_proxy": null,
          "http_proxy": "<REDACTED>",
          "https_proxy": null,
          "metering_timer": 14400,
          "ua_apt_http_proxy": null,
          "ua_apt_https_proxy": null,
          "update_messaging_timer": 21600,
          "vulnerability_data_url_prefix": "https://security-metadata.canonical.com/oval/"
        },
        "meta": {
          "environment_vars": []
        },
        "type": "Config"
      }
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |
