Feature: pro config sub-command

    @series.xenial
    @series.jammy
    @series.kinetic
    @uses.config.machine_type.lxd-container
    Scenario Outline: old ua_config in uaclient.conf is still supported
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `pro config show` with sudo
        Then I will see the following on stdout:
        """
        http_proxy              None
        https_proxy             None
        apt_http_proxy          None
        apt_https_proxy         None
        ua_apt_http_proxy       None
        ua_apt_https_proxy      None
        global_apt_http_proxy   None
        global_apt_https_proxy  None
        update_messaging_timer  21600
        metering_timer          14400
        apt_news                True
        apt_news_url            https://motd.ubuntu.com/aptnews.json
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
        http_proxy              None
        https_proxy             None
        apt_http_proxy          None
        apt_https_proxy         None
        ua_apt_http_proxy       None
        ua_apt_https_proxy      None
        global_apt_http_proxy   None
        global_apt_https_proxy  None
        update_messaging_timer  21600
        metering_timer          14400
        apt_news                False
        apt_news_url            https://motd.ubuntu.com/aptnews.json
        """
        Then I will see the following on stderr:
        """
        """
        Examples: ubuntu release
            | release |
            | xenial  |
            | jammy   |
            | kinetic |
