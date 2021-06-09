@uses.config.contract_token
Feature: Attach command when proxy is configured

    @series.lts
    Scenario Outline: Attach command when proxy is configured
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I launch a `focal` `proxy` machine
        And I run `apt install squid -y` `with sudo` on the `proxy` machine
        And I add this text on `/etc/squid/squid.conf` on `proxy` above `http_access deny all`:
            """
            acl all src 0.0.0.0\/0\nhttp_access allow all
            """
        And I run `systemctl restart squid.service` `with sudo` on the `proxy` machine
        And I configure uaclient `http` proxy to use `proxy` machine
        And I configure uaclient `https` proxy to use `proxy` machine
        And I verify `/var/log/squid/access.log` is empty on `proxy` machine
        And I attach `contract_token` with sudo
        And I run `cat /var/log/squid/access.log` `with sudo` on the `proxy` machine
        Then stdout matches regexp:
        """
        .*CONNECT contracts.canonical.com.*
        """

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
