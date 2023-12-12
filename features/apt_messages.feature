Feature: APT Messages

    @uses.config.contract_token
    Scenario Outline: APT JSON Hook prints package counts correctly on xenial
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        When I apt update
        When I apt upgrade
        When I apt install `<standard-pkg>`
        When I apt upgrade
        Then stdout matches regexp:
        """
        1 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        1 standard LTS security update

        """

        When I apt install `<infra-pkg>`
        When I apt upgrade
        Then stdout matches regexp:
        """
        2 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        2 esm-infra security updates

        """

        When I apt install `<apps-pkg>`
        When I apt upgrade
        Then stdout matches regexp:
        """
        1 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        1 esm-apps security update

        """

        When I apt install `<standard-pkg> <infra-pkg>`
        When I apt upgrade
        Then stdout matches regexp:
        """
        3 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        1 standard LTS security update and 2 esm-infra security updates

        """

        When I apt install `<standard-pkg> <apps-pkg>`
        When I apt upgrade
        Then stdout matches regexp:
        """
        2 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        1 standard LTS security update and 1 esm-apps security update

        """

        When I apt install `<infra-pkg> <apps-pkg>`
        When I apt upgrade
        Then stdout matches regexp:
        """
        3 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        2 esm-infra security updates and 1 esm-apps security update

        """

        When I apt install `<standard-pkg> <infra-pkg> <apps-pkg>`
        When I apt upgrade
        Then stdout matches regexp:
        """
        4 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        1 standard LTS security update, 2 esm-infra security updates and 1 esm-apps security update

        """

        When I apt upgrade
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
           | release | machine_type  | standard-pkg         | infra-pkg                                            | apps-pkg     |
           | xenial  | lxd-container | wget=1.17.1-1ubuntu1 | curl=7.47.0-1ubuntu2 libcurl3-gnutls=7.47.0-1ubuntu2 | hello=2.10-1 |

    @uses.config.contract_token
    Scenario Outline: APT Hook advertises esm-infra on upgrade
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I apt update
        When I apt upgrade
        When I apt autoremove
        When I run `pro config set apt_news=false` with sudo
        When I run `pro refresh messages` with sudo
        When I apt upgrade
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        The following security updates require Ubuntu Pro with 'esm-infra' enabled:
          ([-+.\w\s]*)
        Learn more about Ubuntu Pro for <version>\.04 at https:\/\/ubuntu\.com\/<version>-04
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded\.
        """
        When I apt-get upgrade
        Then I will see the following on stdout:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """
        When I attach `contract_token` with sudo
        When I dry run apt upgrade
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        The following packages will be upgraded:
        """
        When I apt upgrade
        When I run `pro detach --assume-yes` with sudo
        When I run `pro refresh messages` with sudo
        When I apt upgrade
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded\.
        """
        Examples: ubuntu release
          | release | machine_type  | version |
          | xenial  | lxd-container | 16      |
          | bionic  | lxd-container | 18      |

    @uses.config.contract_token
    Scenario Outline: APT Hook advertises esm-apps on upgrade
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I apt update
        When I apt upgrade including phased updates
        When I apt autoremove
        When I apt install `<package>`
        When I run `pro config set apt_news=false` with sudo
        When I run `pro refresh messages` with sudo
        When I apt upgrade
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        Get <more_msg> through Ubuntu Pro with 'esm-apps' enabled:
          <package>
        <learn_more_msg>
        0 upgraded, 0 newly installed, 0 to remove and \d+ not upgraded.
        """
        When I apt-get upgrade
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        0 upgraded, 0 newly installed, 0 to remove and \d+ not upgraded.
        """
        When I attach `contract_token` with sudo
        When I dry run apt upgrade
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        The following packages will be upgraded:
          <package>
        """
        When I apt upgrade
        When I run `pro detach --assume-yes` with sudo
        When I run `pro refresh messages` with sudo
        When I apt upgrade
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        0 upgraded, 0 newly installed, 0 to remove and \d+ not upgraded\.
        """
        Examples: ubuntu release
          | release | machine_type  | package | more_msg                | learn_more_msg                                                    |
          | focal   | lxd-container | hello   | another security update | Learn more about Ubuntu Pro at https://ubuntu.com/pro             |
          | jammy   | lxd-container | hello   | another security update | Learn more about Ubuntu Pro at https://ubuntu.com/pro             |

    @uses.config.contract_token
    Scenario Outline: APT News
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        # On interim releases we will not enable any service, so we need a manual apt update
        When I apt update
        When I apt upgrade including phased updates
        When I apt autoremove
        When I apt install `jq`
        When I run `pro detach --assume-yes` with sudo

        Given a `focal` `<machine_type>` machine named `apt-news-server`
        When I apt update on the `apt-news-server` machine
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
        When I run `pro refresh messages` with sudo
        When I apt upgrade
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
        When I run shell command `pro api u.apt_news.current_news.v1 | jq .data.attributes.current_news` as non-root
        Then I will see the following on stdout
        """
        "one"
        """

        # Test that it is not shown in apt-get output
        When I apt-get upgrade
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
        When I apt update
        When I apt upgrade
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
        When I run shell command `pro api u.apt_news.current_news.v1 | jq .data.attributes.current_news` as non-root
        Then I will see the following on stdout
        """
        "one"
        """
        
        # manual refresh gets new message
        When I run `pro refresh messages` with sudo
        When I apt upgrade
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
        When I run shell command `pro api u.apt_news.current_news.v1 | jq .data.attributes.current_news` as non-root
        Then I will see the following on stdout
        """
        "one\ntwo\nthree"
        """
        
        # creates /run/ubuntu-advantage and /var/lib/ubuntu-advantage/messages if not there
        When I run `rm -rf /run/ubuntu-advantage` with sudo
        When I run `rm -rf /var/lib/ubuntu-advantage/messages` with sudo
        When I run `rm /var/lib/apt/periodic/update-success-stamp` with sudo
        When I apt update
        # the apt-news.service unit runs in the background, give it some time to fetch the json file
        When I wait `5` seconds
        When I apt upgrade
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
        When I run shell command `pro api u.apt_news.current_news.v1 | jq .data.attributes.current_news` as non-root
        Then I will see the following on stdout
        """
        "one\ntwo\nthree"
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
        When I run `pro refresh messages` with sudo
        When I apt upgrade
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """
        When I run shell command `pro api u.apt_news.current_news.v1 | jq .data.attributes.current_news` as non-root
        Then I will see the following on stdout
        """
        null
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
        When I run `pro refresh messages` with sudo
        When I apt upgrade
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """
        When I run shell command `pro api u.apt_news.current_news.v1 | jq .data.attributes.current_news` as non-root
        Then I will see the following on stdout
        """
        null
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
        When I run `pro refresh messages` with sudo
        When I apt upgrade
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """
        When I run shell command `pro api u.apt_news.current_news.v1 | jq .data.attributes.current_news` as non-root
        Then I will see the following on stdout
        """
        null
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
        When I run `pro refresh messages` with sudo
        When I apt upgrade
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
        When I run shell command `pro api u.apt_news.current_news.v1 | jq .data.attributes.current_news` as non-root
        Then I will see the following on stdout
        """
        "one"
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
        When I run `pro refresh messages` with sudo
        When I apt upgrade
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """
        When I run shell command `pro api u.apt_news.current_news.v1 | jq .data.attributes.current_news` as non-root
        Then I will see the following on stdout
        """
        null
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
        When I run `pro refresh messages` with sudo
        When I apt upgrade
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """
        When I run shell command `pro api u.apt_news.current_news.v1 | jq .data.attributes.current_news` as non-root
        Then I will see the following on stdout
        """
        null
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
        When I apt upgrade
        When I set the machine token overlay to the following yaml
        """
        machineTokenInfo:
          contractInfo:
            effectiveTo: $behave_var{today +2}
        """
        # test that apt update will trigger hook to update apt_news for local override
        When I run `rm -f /var/lib/apt/periodic/update-success-stamp` with sudo
        When I apt update
        # the apt-news.service unit runs in the background, give it some time to fetch the json file
        When I wait `5` seconds
        When I apt upgrade
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # CAUTION: Your Ubuntu Pro subscription will expire in 2 days.
        # Renew your subscription at https://ubuntu.com/pro/dashboard to ensure
        # continued security coverage for your applications.
        #
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """
        When I run shell command `pro api u.apt_news.current_news.v1 | jq .data.attributes.current_news` as non-root
        Then I will see the following on stdout
        """
        "CAUTION: Your Ubuntu Pro subscription will expire in 2 days.\nRenew your subscription at https://ubuntu.com/pro/dashboard to ensure\ncontinued security coverage for your applications."
        """
        When I set the machine token overlay to the following yaml
        """
        machineTokenInfo:
          contractInfo:
            effectiveTo: $behave_var{today -3}
        """
        When I run `pro refresh messages` with sudo
        When I apt upgrade
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # CAUTION: Your Ubuntu Pro subscription expired on \d+ \w+ \d+.
        # Renew your subscription at https:\/\/ubuntu.com\/pro\/dashboard to ensure
        # continued security coverage for your applications.
        # Your grace period will expire in 11 days.
        #
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """
        When I run shell command `pro api u.apt_news.current_news.v1 | jq .data.attributes.current_news` as non-root
        Then stdout matches regexp:
        """
        "CAUTION: Your Ubuntu Pro subscription expired on \d+ \w+ \d+.\\nRenew your subscription at https:\/\/ubuntu.com\/pro\/dashboard to ensure\\ncontinued security coverage for your applications.\\nYour grace period will expire in 11 days."
        """
        When I set the machine token overlay to the following yaml
        """
        machineTokenInfo:
          contractInfo:
            effectiveTo: $behave_var{today -20}
        """
        When I run `pro refresh messages` with sudo
        When I apt upgrade
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # *Your Ubuntu Pro subscription has EXPIRED*
        # Renew your subscription at https://ubuntu.com/pro/dashboard
        #
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """
        When I run shell command `pro api u.apt_news.current_news.v1 | jq .data.attributes.current_news` as non-root
        Then I will see the following on stdout
        """
        "*Your Ubuntu Pro subscription has EXPIRED*\nRenew your subscription at https://ubuntu.com/pro/dashboard"
        """
        When I create the file `/var/lib/ubuntu-advantage/machine-token-overlay.json` with the following:
        """
        {
            "machineTokenInfo": {
                "contractInfo": {
                    "effectiveTo": null
                }
            }
        }
        """
        When I run `pro refresh messages` with sudo
        When I apt upgrade
        Then I will see the following on stdout
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # *Your Ubuntu Pro subscription has EXPIRED*
        # Renew your subscription at https://ubuntu.com/pro/dashboard
        #
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """
        When I run shell command `pro api u.apt_news.current_news.v1 | jq .data.attributes.current_news` as non-root
        Then I will see the following on stdout
        """
        "*Your Ubuntu Pro subscription has EXPIRED*\nRenew your subscription at https://ubuntu.com/pro/dashboard"
        """
        Examples: ubuntu release
          | release | machine_type  |
          | xenial  | lxd-container |
          | bionic  | lxd-container |
          | focal   | lxd-container |
          | jammy   | lxd-container |
          | mantic  | lxd-container |

    Scenario Outline: Cloud and series-specific URLs
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I apt update
        When I apt install `ansible`
        # Update after installing to make sure messages are there
        When I apt update
        When I dry run apt upgrade
        Then stdout contains substring:
        """
        <msg>
        """
        Examples: release-per-machine-type
          | release | machine_type  | msg                                                                              |
          | xenial  | aws.generic   | Learn more about Ubuntu Pro for 16.04 at https://ubuntu.com/16-04                |
          | xenial  | azure.generic | Learn more about Ubuntu Pro for 16.04 on Azure at https://ubuntu.com/16-04/azure |
          | xenial  | gcp.generic   | Learn more about Ubuntu Pro for 16.04 at https://ubuntu.com/16-04                |
          | bionic  | aws.generic   | Learn more about Ubuntu Pro for 18.04 at https://ubuntu.com/18-04                |
          | bionic  | azure.generic | Learn more about Ubuntu Pro for 18.04 on Azure at https://ubuntu.com/18-04/azure |
          | bionic  | gcp.generic   | Learn more about Ubuntu Pro for 18.04 at https://ubuntu.com/18-04                |
          | focal   | aws.generic   | Learn more about Ubuntu Pro on AWS at https://ubuntu.com/aws/pro                 |
          | focal   | azure.generic | Learn more about Ubuntu Pro on Azure at https://ubuntu.com/azure/pro             |
          | focal   | gcp.generic   | Learn more about Ubuntu Pro on GCP at https://ubuntu.com/gcp/pro                 |

    @uses.config.contract_token
    Scenario Outline: APT Hook do not advertises esm-apps on upgrade for interim releases
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I apt update
        When I apt upgrade including phased updates
        When I apt autoremove
        When I apt install `hello`
        When I run `pro config set apt_news=false` with sudo
        When I run `pro refresh messages` with sudo
        When I apt upgrade
        Then stdout does not match regexp:
        """
        Get more security updates through Ubuntu Pro with 'esm-apps' enabled:
        """
        When I apt-get upgrade
        Then I will see the following on stdout:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """
        When I attach `contract_token` with sudo
        When I dry run apt upgrade
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded\.
        """
        When I apt upgrade
        When I run `pro detach --assume-yes` with sudo
        When I run `pro refresh messages` with sudo
        When I apt upgrade
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded\.
        """
        Examples: ubuntu release
          | release | machine_type  |
          | mantic  | lxd-container |
