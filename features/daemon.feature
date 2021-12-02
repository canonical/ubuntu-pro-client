Feature: UA daemon starts and stops jobs appropriately

    @series.all
    @uses.config.machine_type.lxd.container
    @uses.config.machine_type.aws.generic
    @uses.config.machine_type.azure.generic
    Scenario Outline: Check daemon exits cleanly on platforms with no work
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
        Then stdout matches regexp:
        """
        started 0 threads
        """
        Then stdout matches regexp:
        """
        daemon finished
        """
        When I run `truncate -s 0 /var/log/ubuntu-advantage-daemon.log` with sudo
        When I append the following on uaclient config
        """
        ua_config:
            should_poll_for_licenses: true
        """
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
        Then stdout matches regexp:
        """
        started 0 threads
        """
        Then stdout matches regexp:
        """
        daemon finished
        """
        Examples: version
            | release |
            | xenial  |
            | bionic  |
            | focal   |
            | hirsute |
            | impish |

    @series.all
    @uses.config.machine_type.gcp.generic
    Scenario Outline: Check gcp_pollin_fn starts on gcp
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
        Then stdout matches regexp:
        """
        started 0 threads
        """
        Then stdout matches regexp:
        """
        daemon finished
        """
        When I run `truncate -s 0 /var/log/ubuntu-advantage-daemon.log` with sudo
        When I append the following on uaclient config
        """
        ua_config:
            should_poll_for_licenses: true
        """
        When I run `systemctl restart ua.service` with sudo
        When I wait `1` seconds
        Then I verify that running `systemctl status ua.service` `with sudo` exits `0`
        Then stdout matches regexp:
        """
        Active: active \(running\)
        """
        When I run `cat /var/log/ubuntu-advantage-daemon.log` with sudo
        Then stdout matches regexp:
        """
        daemon started
        """
        Then stdout matches regexp:
        """
        started 1 threads
        """
        Then stdout does not match regexp:
        """
        daemon finished
        """
        Examples: version
            | release |
            | xenial  |
            | bionic  |
            | focal   |
            | hirsute |
            | impish |
