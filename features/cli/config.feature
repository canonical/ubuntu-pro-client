Feature: CLI config command

  # earliest, latest lts[, latest stable]
  @arm64
  Scenario Outline: old ua_config in uaclient.conf is still supported
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro config show` with sudo
    Then I will see the following on stdout:
      """
      http_proxy                     None
      https_proxy                    None
      apt_http_proxy                 None
      apt_https_proxy                None
      ua_apt_http_proxy              None
      ua_apt_https_proxy             None
      global_apt_http_proxy          None
      global_apt_https_proxy         None
      update_messaging_timer         21600
      metering_timer                 14400
      apt_news                       True
      apt_news_url                   https://motd.ubuntu.com/aptnews.json
      vulnerability_data_url_prefix  https://security-metadata.canonical.com/oval/
      lxd_guest_attach               off
      """
    Then I will see the following on stderr:
      """
      """
    When I append the following on uaclient config:
      """
      ua_config: {apt_news: false}
      """
    When I run `pro config show` with sudo
    Then I will see the following on stdout:
      """
      http_proxy                     None
      https_proxy                    None
      apt_http_proxy                 None
      apt_https_proxy                None
      ua_apt_http_proxy              None
      ua_apt_https_proxy             None
      global_apt_http_proxy          None
      global_apt_https_proxy         None
      update_messaging_timer         21600
      metering_timer                 14400
      apt_news                       False
      apt_news_url                   https://motd.ubuntu.com/aptnews.json
      vulnerability_data_url_prefix  https://security-metadata.canonical.com/oval/
      lxd_guest_attach               off
      """
    Then I will see the following on stderr:
      """
      """
    When I verify that running `pro config invalid` `as non-root` exits `2`
    Then I will see the following on stdout:
      """
      """
    Then if `<release>` in `xenial or jammy or noble` and stderr contains substring:
      """
      usage: pro config [-h] {show,set,unset} ...
      pro config: error: argument command: invalid choice: 'invalid' (choose from 'show', 'set', 'unset')
      """
    Then if `<release>` in `plucky` and stderr contains substring:
      """
      usage: pro config [-h] {show,set,unset} ...
      pro config: error: argument command: invalid choice: 'invalid' (choose from show, set, unset)
      """

    Examples: ubuntu release
      | release  | machine_type  |
      | xenial   | lxd-container |
      | jammy    | lxd-container |
      | noble    | lxd-container |
      | plucky   | lxd-container |
      | questing | lxd-container |
