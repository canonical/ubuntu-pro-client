Feature: UA daemon starts and stops jobs appropriately

    # TODO: Replace this as soon as the daemon does something real
    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Check daemon starts and restarts
        Given a `<release>` machine with ubuntu-advantage-tools installed
        Then I verify that running `systemctl status ua.service` `with sudo` exits `3`
        Then stdout matches regexp:
        """
        code=exited, status=0/SUCCESS
        """
        When I run `cat /var/log/ubuntu-advantage-daemon.log` with sudo
        Then stdout matches regexp:
        """
        daemon started
        """
        When I run `truncate -s 0 /var/log/ubuntu-advantage-daemon.log` with sudo
        When I run `systemctl restart ua.service` with sudo
        When I wait `1` seconds
        Then I verify that running `systemctl status ua.service` `with sudo` exits `3`
        Then stdout matches regexp:
        """
        code=exited, status=0/SUCCESS
        """
        When I run `cat /var/log/ubuntu-advantage-daemon.log` with sudo
        Then stdout matches regexp:
        """
        daemon started
        """
        Examples: version
            | release |
            | xenial  |
            | bionic  |
            | focal   |
            | hirsute |
            | impish |
