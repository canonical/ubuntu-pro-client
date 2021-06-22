@uses.config.contract_token
Feature: Proxy configuration

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

        When I run `truncate -s 0 /var/log/squid/access.log` `with sudo` on the `proxy` machine
        And I run `ua detach --assume-yes` with sudo
        And I configure uaclient `apt_http` proxy to use `proxy` machine
        And I configure uaclient `apt_https` proxy to use `proxy` machine
        And I verify `/var/log/squid/access.log` is empty on `proxy` machine
        Then I verify that no files exist matching `/etc/apt/apt.conf.d/90ubuntu-advantage-aptproxy`
        When I attach `contract_token` with sudo
        Then I verify that files exist matching `/etc/apt/apt.conf.d/90ubuntu-advantage-aptproxy`
        When I run `cat /etc/apt/apt.conf.d/90ubuntu-advantage-aptproxy` with sudo
        Then stdout matches regexp:
        """
        /\*
         \* Autogenerated by ubuntu-advantage-tools
         \* Do not edit this file directly
         \*
         \* To change what ubuntu-advantage-tools sets here, edit the apt_http_proxy
         \* and apt_https_proxy fields in /etc/ubuntu-advantage/uaclient.conf.
         \*/
        Acquire::http::Proxy ".*";
        Acquire::https::Proxy ".*";
        """
        When I run `apt update` with sudo
        And I run `cat /var/log/squid/access.log` `with sudo` on the `proxy` machine
        Then stdout matches regexp:
        """
        .*GET.*ubuntu.com/ubuntu/dists.*
        """
        When I append the following on uaclient config
        """
        ua_config:
            apt_http_proxy: ""
            apt_https_proxy: ""
        """
        And I run `ua enable cis` with sudo
        Then I verify that no files exist matching `/etc/apt/apt.conf.d/90ubuntu-advantage-aptproxy`

        When I run `ua disable cis` with sudo
        And I create the file `/etc/apt/apt.conf.d/50-testproxy` with the following
        """
        Acquire::http::Proxy "http://localhost:1234";
        Acquire::https::Proxy "http://localhost:12345";
        """
        And I configure uaclient `apt_http` proxy to use `proxy` machine
        And I configure uaclient `apt_https` proxy to use `proxy` machine
        When I run `ua enable cis` with sudo, and provide the following stdin
        """
        n
        y

        """
        Then stdout matches regexp:
        """
        Existing apt http proxy set to "http://localhost:1234".
        Do you want to change it to ".*"\? \(y/N\) Existing apt https proxy set to "http://localhost:12345".
        Do you want to change it to ".*"\? \(y/N\)
        """
        When I run `cat /etc/apt/apt.conf.d/90ubuntu-advantage-aptproxy` with sudo
        Then stdout matches regexp:
        """
        /\*
         \* Autogenerated by ubuntu-advantage-tools
         \* Do not edit this file directly
         \*
         \* To change what ubuntu-advantage-tools sets here, edit the apt_http_proxy
         \* and apt_https_proxy fields in /etc/ubuntu-advantage/uaclient.conf.
         \*/
        Acquire::https::Proxy ".*";
        """

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |

    @series.xenial
    @series.bionic
    @series.focal
    @uses.config.machine_type.lxd.vm
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
        And I run `canonical-livepatch config check-interval=0` with sudo
        And I run `canonical-livepatch refresh` with sudo
        And I run `cat /var/log/squid/access.log` `with sudo` on the `proxy` machine
        Then stdout matches regexp:
        """
        .*CONNECT contracts.canonical.com.*
        """
        When I run `cat /var/log/squid/access.log` `with sudo` on the `proxy` machine
        Then stdout matches regexp:
        """
        .*CONNECT api.snapcraft.io:443.*
        """
        When I run `sleep 120` as non-root
        And I run `cat /var/log/squid/access.log` `with sudo` on the `proxy` machine
        Then stdout matches regexp:
        """
        .*CONNECT livepatch.canonical.com:443.*
        """

        When I run `ua disable livepatch --assume-yes` with sudo
        And I run `snap set system proxy.http=http://localhost:1234` with sudo
        And I run `canonical-livepatch config https-proxy=http://localhost:12345` with sudo
        And I run `ua enable livepatch` with sudo, and provide the following stdin
        """
        n
        y

        """
        Then stdout matches regexp:
        """
        Existing snap http proxy set to "http://localhost:1234".
        Do you want to change it to ".*"\? \(y/N\) Existing livepatch https proxy set to "http://localhost:12345".
        Do you want to change it to ".*"\? \(y/N\)
        """
        When I run `snap get system proxy.http` with sudo
        Then stdout matches regexp:
        """
        http://localhost:1234
        """
        When I run `canonical-livepatch config` with sudo
        Then stdout matches regexp:
        """
        https-proxy: http://10.*
        """
        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
