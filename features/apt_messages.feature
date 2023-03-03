Feature: APT Messages

    @series.xenial
    @uses.config.machine_type.lxd.container
    Scenario Outline: APT JSON Hook prints package counts correctly on xenial
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        When I run `apt-get update` with sudo
        When I run `apt-get upgrade -y` with sudo

        When I run `apt-get install -y --allow-downgrades <standard-pkg>` with sudo
        When I run `apt upgrade -y` with sudo
        Then stdout matches regexp:
        """
        2 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        2 standard LTS security updates

        """

        When I run `apt-get install -y --allow-downgrades <infra-pkg>` with sudo
        When I run `apt upgrade -y` with sudo
        Then stdout matches regexp:
        """
        2 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        2 esm-infra security updates

        """

        When I run `apt-get install -y --allow-downgrades <apps-pkg>` with sudo
        When I run `apt upgrade -y` with sudo
        Then stdout matches regexp:
        """
        1 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        1 esm-apps security update

        """

        When I run `apt-get install -y --allow-downgrades <standard-pkg>` with sudo
        When I run `apt-get install -y --allow-downgrades <infra-pkg>` with sudo
        When I run `apt upgrade -y` with sudo
        Then stdout matches regexp:
        """
        4 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        2 standard LTS security updates and 2 esm-infra security updates

        """

        When I run `apt-get install -y --allow-downgrades <standard-pkg>` with sudo
        When I run `apt-get install -y --allow-downgrades <apps-pkg>` with sudo
        When I run `apt upgrade -y` with sudo
        Then stdout matches regexp:
        """
        3 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        2 standard LTS security updates and 1 esm-apps security update

        """

        When I run `apt-get install -y --allow-downgrades <infra-pkg>` with sudo
        When I run `apt-get install -y --allow-downgrades <apps-pkg>` with sudo
        When I run `apt upgrade -y` with sudo
        Then stdout matches regexp:
        """
        3 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        2 esm-infra security updates and 1 esm-apps security update

        """

        When I run `apt-get install -y --allow-downgrades <standard-pkg>` with sudo
        When I run `apt-get install -y --allow-downgrades <infra-pkg>` with sudo
        When I run `apt-get install -y --allow-downgrades <apps-pkg>` with sudo
        When I run `apt upgrade -y` with sudo
        Then stdout matches regexp:
        """
        5 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        2 standard LTS security updates, 2 esm-infra security updates and 1 esm-apps security update

        """

        When I run `apt upgrade -y` with sudo
        Then stdout matches regexp:
        """
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """
        Then stdout does not match regexp:
        """
        standard LTS security update
        """
        Then stdout does not match regexp:
        """
        esm-infra
        """
        Then stdout does not match regexp:
        """
        esm-apps
        """

        Examples: ubuntu release
           | release | standard-pkg                                                          | infra-pkg                                            | apps-pkg     |
           | xenial  | accountsservice=0.6.40-2ubuntu10 libaccountsservice0=0.6.40-2ubuntu10 | curl=7.47.0-1ubuntu2 libcurl3-gnutls=7.47.0-1ubuntu2 | hello=2.10-1 |

    @series.xenial
    @uses.config.machine_type.lxd.container
    Scenario Outline: APT Hook advertises esm-infra on upgrade
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get update` with sudo
        When I run `apt-get -y upgrade` with sudo
        When I run `apt-get -y autoremove` with sudo
        When I run `pro config set apt_news=false` with sudo
        When I run `pro refresh messages` with sudo
        When I run `apt upgrade` with sudo
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        The following security updates require Ubuntu Pro with 'esm-infra' enabled:
          ([-+.\w\s]*)
        Learn more about Ubuntu Pro for 16\.04 at https:\/\/ubuntu\.com\/16-04
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded\.
        """
        When I run `apt-get upgrade` with sudo
        Then I will see the following on stdout:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """
        When I attach `contract_token` with sudo
        When I run `apt upgrade --dry-run` with sudo
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        The following packages will be upgraded:
        """
        When I run `apt-get upgrade -y` with sudo
        When I run `pro detach --assume-yes` with sudo
        When I run `pro refresh messages` with sudo
        When I run `apt upgrade` with sudo
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded\.
        """
        Examples: ubuntu release
          | release |
          | xenial  |

    @series.bionic
    @series.focal
    @series.jammy
    @uses.config.machine_type.lxd.container
    Scenario Outline: APT Hook advertises esm-apps on upgrade
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get update` with sudo
        When I run `apt-get -o APT::Get::Always-Include-Phased-Updates=true upgrade -y` with sudo
        When I run `apt-get -y autoremove` with sudo
        When I run `apt-get install <package> -y` with sudo
        When I run `pro config set apt_news=false` with sudo
        When I run `pro refresh messages` with sudo
        When I run `apt upgrade` with sudo
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        Get more security updates through Ubuntu Pro with 'esm-apps' enabled:
          <package>
        Learn more about Ubuntu Pro at https://ubuntu.com/pro
        0 upgraded, 0 newly installed, 0 to remove and \d+ not upgraded.
        """
        When I run `apt-get upgrade` with sudo
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        0 upgraded, 0 newly installed, 0 to remove and \d+ not upgraded.
        """
        When I attach `contract_token` with sudo
        When I run `apt upgrade --dry-run` with sudo
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        The following packages will be upgraded:
          <package>
        """
        When I run `apt-get upgrade -y` with sudo
        When I run `pro detach --assume-yes` with sudo
        When I run `pro refresh messages` with sudo
        When I run `apt upgrade` with sudo
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        0 upgraded, 0 newly installed, 0 to remove and \d+ not upgraded\.
        """
        Examples: ubuntu release
          | release | package |
          | bionic  | ansible |
          | focal   | hello   |
          | jammy   | hello   |

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: APT News
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        When I run `apt-get -o APT::Get::Always-Include-Phased-Updates=true upgrade -y` with sudo
        When I run `apt-get autoremove -y` with sudo
        When I run `pro detach --assume-yes` with sudo

        Given a `focal` machine named `apt-news-server`
        When I run `apt-get update` `with sudo` on the `apt-news-server` machine
        When I apt install `nginx` on the `apt-news-server` machine
        When I run `sed -i "s/gzip on;/gzip on;\n\tgzip_min_length 1;\n\tgzip_types application\/json;\n/" /etc/nginx/nginx.conf` `with sudo` on the `apt-news-server` machine
        When I run `systemctl restart nginx` `with sudo` on the `apt-news-server` machine

        When I run `pro config set apt_news_url=http://$behave_var{machine-ip apt-news-server}/aptnews.json` with sudo

        When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
        """
        {
          "messages": [
            {
              "begin": "$behave_var{today}",
              "lines": [
                "one"
              ]
            }
          ]
        }
        """
        # test is too fast and systemd doesn't like triggering motd-news.service
        # (during pro refresh messages) too frequently
        # So there are "wait"s before each pro refresh messages call
        When I wait `1` seconds
        When I run `pro refresh messages` with sudo
        When I run shell command `rm -f /var/lib/ubuntu-advantage/messages/apt-pre*` with sudo
        When I run `apt upgrade` with sudo
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # one
        #
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """

        # Test that it is not shown in apt-get output
        When I run `apt-get upgrade` with sudo
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """
        When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
        """
        {
          "messages": [
            {
              "begin": "$behave_var{today}",
              "lines": [
                "one",
                "two",
                "three"
              ]
            }
          ]
        }
        """

        # apt update stamp will prevent a apt_news refresh
        When I run `apt-get update` with sudo
        When I run shell command `rm -f /var/lib/ubuntu-advantage/messages/apt-pre*` with sudo
        When I run `apt upgrade` with sudo
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # one
        #
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """

        # manual refresh gets new message
        When I wait `1` seconds
        When I run `pro refresh messages` with sudo
        When I run shell command `rm -f /var/lib/ubuntu-advantage/messages/apt-pre*` with sudo
        When I run `apt upgrade` with sudo
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # one
        # two
        # three
        #
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """

        # creates /run/ubuntu-advantage and /var/lib/ubuntu-advantage/messages if not there
        When I run `rm -rf /run/ubuntu-advantage` with sudo
        When I run `rm -rf /var/lib/ubuntu-advantage/messages` with sudo
        When I run `rm /var/lib/apt/periodic/update-success-stamp` with sudo
        When I run `apt-get update` with sudo
        When I run shell command `rm -f /var/lib/ubuntu-advantage/messages/apt-pre*` with sudo
        When I run `apt upgrade` with sudo
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # one
        # two
        # three
        #
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """

        # more than 3 lines ignored
        When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
        """
        {
          "messages": [
            {
              "begin": "$behave_var{today}",
              "lines": [
                "one",
                "two",
                "three",
                "four"
              ]
            }
          ]
        }
        """
        When I wait `1` seconds
        When I run `pro refresh messages` with sudo
        When I run shell command `rm -f /var/lib/ubuntu-advantage/messages/apt-pre*` with sudo
        When I run `apt upgrade` with sudo
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """

        # more than 77 chars ignored
        When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
        """
        {
          "messages": [
            {
              "begin": "$behave_var{today}",
              "lines": [
                "000000000100000000020000000003000000000400000000050000000006000000000712345678"
              ]
            }
          ]
        }
        """
        When I wait `1` seconds
        When I run `pro refresh messages` with sudo
        When I run shell command `rm -f /var/lib/ubuntu-advantage/messages/apt-pre*` with sudo
        When I run `apt upgrade` with sudo
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """

        # end is respected
        When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
        """
        {
          "messages": [
            {
              "begin": "$behave_var{today -3}",
              "end": "$behave_var{today -1}",
              "lines": [
                "one"
              ]
            }
          ]
        }
        """
        When I wait `1` seconds
        When I run `pro refresh messages` with sudo
        When I run shell command `rm -f /var/lib/ubuntu-advantage/messages/apt-pre*` with sudo
        When I run `apt upgrade` with sudo
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """
        When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
        """
        {
          "messages": [
            {
              "begin": "$behave_var{today -3}",
              "end": "$behave_var{today +1}",
              "lines": [
                "one"
              ]
            }
          ]
        }
        """
        When I wait `1` seconds
        When I run `pro refresh messages` with sudo
        When I run shell command `rm -f /var/lib/ubuntu-advantage/messages/apt-pre*` with sudo
        When I run `apt upgrade` with sudo
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # one
        #
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """

        # begin >30 days ago ignored, even if end is set to future
        When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
        """
        {
          "messages": [
            {
              "begin": "$behave_var{today -31}",
              "end": "$behave_var{today +1}",
              "lines": [
                "one"
              ]
            }
          ]
        }
        """
        When I wait `1` seconds
        When I run `pro refresh messages` with sudo
        When I run shell command `rm -f /var/lib/ubuntu-advantage/messages/apt-pre*` with sudo
        When I run `apt upgrade` with sudo
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """

        # begin in future
        When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
        """
        {
          "messages": [
            {
              "begin": "$behave_var{today +1}",
              "lines": [
                "one"
              ]
            }
          ]
        }
        """
        When I wait `1` seconds
        When I run `pro refresh messages` with sudo
        When I run shell command `rm -f /var/lib/ubuntu-advantage/messages/apt-pre*` with sudo
        When I run `apt upgrade` with sudo
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """

        # local apt news overrides for contract expiry notices
        When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
        """
        {
          "messages": [
            {
              "begin": "$behave_var{today}",
              "lines": [
                "one"
              ]
            }
          ]
        }
        """
        When I attach `contract_token` with sudo
        When I run `apt upgrade -y` with sudo
        When I create the file `/tmp/machine-token-overlay.json` with the following:
        """
        {
            "machineTokenInfo": {
                "contractInfo": {
                    "effectiveTo": "$behave_var{today +2}"
                }
            }
        }
        """
        And I append the following on uaclient config:
        """
        features:
          machine_token_overlay: "/tmp/machine-token-overlay.json"
        """
        # test that apt update will trigger hook to update apt_news for local override
        When I run shell command `rm -f /var/lib/apt/periodic/update-success-stamp` with sudo
        When I run `apt-get update` with sudo
        When I run shell command `rm -f /var/lib/ubuntu-advantage/messages/apt-pre*` with sudo
        When I run `apt upgrade` with sudo
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # CAUTION: Your Ubuntu Pro subscription will expire in 2 days.
        # Renew your subscription at https://ubuntu.com/pro to ensure continued
        # security coverage for your applications.
        #
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """
        When I create the file `/tmp/machine-token-overlay.json` with the following:
        """
        {
            "machineTokenInfo": {
                "contractInfo": {
                    "effectiveTo": "$behave_var{today -3}"
                }
            }
        }
        """
        When I wait `1` seconds
        When I run `pro refresh messages` with sudo
        When I run `apt upgrade` with sudo
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # CAUTION: Your Ubuntu Pro subscription expired on \d+ \w+ \d+.
        # Renew your subscription at https:\/\/ubuntu.com\/pro to ensure continued
        # security coverage for your applications.
        # Your grace period will expire in 11 days.
        #
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """
        When I create the file `/tmp/machine-token-overlay.json` with the following:
        """
        {
            "machineTokenInfo": {
                "contractInfo": {
                    "effectiveTo": "$behave_var{today -20}"
                }
            }
        }
        """
        When I wait `1` seconds
        When I run `pro refresh messages` with sudo
        When I run `apt upgrade` with sudo
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # *Your Ubuntu Pro subscription has EXPIRED*
        # Renew your service at https://ubuntu.com/pro
        #
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """
        When I create the file `/tmp/machine-token-overlay.json` with the following:
        """
        {
            "machineTokenInfo": {
                "contractInfo": {
                    "effectiveTo": null
                }
            }
        }
        """
        When I wait `1` seconds
        When I run `pro refresh messages` with sudo
        When I run `apt upgrade` with sudo
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # *Your Ubuntu Pro subscription has EXPIRED*
        # Renew your service at https://ubuntu.com/pro
        #
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """

        # detach and pretend to be DGX OS to check the special DGX message
        When I create the file `/tmp/machine-token-overlay.json` with the following:
        """
        {}
        """
        When I run `pro detach --assume-yes` with sudo
        When I run `touch /etc/dgx-release` with sudo
        When I wait `1` seconds
        When I run `pro refresh messages` with sudo
        When I run `apt upgrade` with sudo
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # Your DGX contract entitles you to ESM updates.
        # Please contact your NVIDIA account manager to get your Pro subscription.
        #
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """
        Examples: ubuntu release
          | release |
          | xenial  |
          | bionic  |
          | focal   |
          | jammy   |

    @series.xenial
    @series.bionic
    @uses.config.machine_type.aws.generic
    Scenario Outline: AWS URLs
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get update` with sudo
        When I run `pro refresh messages` with sudo
        When I run `apt upgrade --dry-run` with sudo
        Then stdout matches regexp:
        """
        <msg>
        """
        Examples: ubuntu release
          | release | msg                                                                    |
          | xenial  | Learn more about Ubuntu Pro for 16\.04 at https:\/\/ubuntu\.com\/16-04 |
          | bionic  | Learn more about Ubuntu Pro on AWS at https:\/\/ubuntu\.com\/aws\/pro  |

    @series.xenial
    @series.bionic
    @uses.config.machine_type.azure.generic
    Scenario Outline: Azure URLs
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get update` with sudo
        When I run `pro refresh messages` with sudo
        When I run `apt upgrade --dry-run` with sudo
        Then stdout matches regexp:
        """
        <msg>
        """
        Examples: ubuntu release
          | release | msg                                                                                    |
          | xenial  | Learn more about Ubuntu Pro for 16\.04 on Azure at https:\/\/ubuntu\.com\/16-04\/azure |
          | bionic  | Learn more about Ubuntu Pro on Azure at https:\/\/ubuntu\.com\/azure\/pro              |

    @series.xenial
    @series.bionic
    @uses.config.machine_type.gcp.generic
    Scenario Outline: GCP URLs
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get update` with sudo
        When I run `pro refresh messages` with sudo
        When I run `apt upgrade --dry-run` with sudo
        Then stdout matches regexp:
        """
        <msg>
        """
        Examples: ubuntu release
          | release | msg                                                                    |
          | xenial  | Learn more about Ubuntu Pro for 16\.04 at https:\/\/ubuntu\.com\/16-04 |
          | bionic  | Learn more about Ubuntu Pro on GCP at https:\/\/ubuntu\.com\/gcp\/pro  |
