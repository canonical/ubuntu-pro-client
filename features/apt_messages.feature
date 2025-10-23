Feature: APT Messages

  @uses.config.contract_token @arm64
  Scenario Outline: APT JSON Hook prints package counts correctly on xenial
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
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
      | release | machine_type  | standard-pkg              | infra-pkg                                            | apps-pkg     |
      | xenial  | lxd-container | apparmor=2.10.95-0ubuntu2 | curl=7.47.0-1ubuntu2 libcurl3-gnutls=7.47.0-1ubuntu2 | hello=2.10-1 |

  @uses.config.contract_token
  Scenario Outline: APT Hook advertises esm-infra on upgrade
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I remove support for `backports` in APT
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
      <ad_message>
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
    When I apt upgrade on a dry run
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
      | release | machine_type  | ad_message                                                                                   |
      | xenial  | lxd-container | Learn more about Ubuntu Pro for <version>\.04 at https:\/\/ubuntu\.com\/<version>-04         |
      | bionic  | lxd-container | Learn more about Ubuntu Pro for <version>\.04 at https:\/\/ubuntu\.com\/<version>-04         |
      | focal   | lxd-container | Learn more about Ubuntu Pro at https:\/\/ubuntu\.com\/pro                                    |

  @uses.config.contract_token
  Scenario Outline: APT Hook advertises esm-apps on upgrade
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
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
    When I apt upgrade on a dry run
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
      | release | machine_type  | package | more_msg                | learn_more_msg                                        |
      # TODO add noble when there is a package available in esm with a higher version than in noble (not true of hello)
      # | noble   | lxd-container | hello   | another security update | Learn more about Ubuntu Pro at https://ubuntu.com/pro |
      | jammy   | lxd-container | hello   | another security update | Learn more about Ubuntu Pro at https://ubuntu.com/pro |
      | jammy   | wsl           | hello   | another security update | Learn more about Ubuntu Pro at https://ubuntu.com/pro |

  @uses.config.contract_token
  Scenario Outline: APT News
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    When I remove support for `backports` in APT
    When I apt upgrade including phased updates
    When I apt autoremove
    When I apt install `jq`
    When I run `pro detach --assume-yes` with sudo
    # We are doing this because ESM pin might prevent some packages to be upgraded (i.e.
    # distro-info-data)
    When I apt dist-upgrade
    Given a `focal` `<machine_type>` machine named `apt-news-server`
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
    Then I will see the following on stdout:
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
    Then I will see the following on stdout:
      """
      "one"
      """
    # Test that it is not shown in apt-get output
    When I apt-get upgrade
    Then I will see the following on stdout:
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
    Then I will see the following on stdout:
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
    Then I will see the following on stdout:
      """
      "one"
      """
    # manual refresh gets new message
    When I run `pro refresh messages` with sudo
    When I apt upgrade
    Then I will see the following on stdout:
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
    Then I will see the following on stdout:
      """
      "one\ntwo\nthree"
      """
    # creates /run/ubuntu-advantage and /var/lib/ubuntu-advantage/messages if not there
    When I run `rm -rf /run/ubuntu-advantage` with sudo
    When I run `rm -rf /var/lib/ubuntu-advantage/messages` with sudo
    When I run `rm /var/lib/apt/periodic/update-success-stamp` with sudo
    When I run `rm -rf /var/lib/apt/lists/` with sudo
    When I apt update
    # the apt-news.service unit runs in the background, give it some time to fetch the json file
    When I wait `5` seconds
    When I apt upgrade
    Then I will see the following on stdout:
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
    Then I will see the following on stdout:
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
    Then I will see the following on stdout:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      Calculating upgrade...
      0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
      """
    When I run shell command `pro api u.apt_news.current_news.v1 | jq .data.attributes.current_news` as non-root
    Then I will see the following on stdout:
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
    Then I will see the following on stdout:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      Calculating upgrade...
      0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
      """
    When I run shell command `pro api u.apt_news.current_news.v1 | jq .data.attributes.current_news` as non-root
    Then I will see the following on stdout:
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
    Then I will see the following on stdout:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      Calculating upgrade...
      0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
      """
    When I run shell command `pro api u.apt_news.current_news.v1 | jq .data.attributes.current_news` as non-root
    Then I will see the following on stdout:
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
    Then I will see the following on stdout:
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
    Then I will see the following on stdout:
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
    Then I will see the following on stdout:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      Calculating upgrade...
      0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
      """
    When I run shell command `pro api u.apt_news.current_news.v1 | jq .data.attributes.current_news` as non-root
    Then I will see the following on stdout:
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
    Then I will see the following on stdout:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      Calculating upgrade...
      0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
      """
    When I run shell command `pro api u.apt_news.current_news.v1 | jq .data.attributes.current_news` as non-root
    Then I will see the following on stdout:
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
    Then I will see the following on stdout:
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
    Then I will see the following on stdout:
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
    Then I will see the following on stdout:
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
    Then I will see the following on stdout:
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
    Then I will see the following on stdout:
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
    Then I will see the following on stdout:
      """
      "*Your Ubuntu Pro subscription has EXPIRED*\nRenew your subscription at https://ubuntu.com/pro/dashboard"
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | xenial  | lxd-vm        |
      | bionic  | lxd-container |
      | bionic  | lxd-vm        |
      | focal   | lxd-container |
      | focal   | lxd-vm        |
      | jammy   | lxd-container |
      | jammy   | lxd-vm        |
      | noble   | lxd-container |
      | noble   | lxd-vm        |

  # This is a subset of the above test, only checking proper outputs for Plucky
  # At some point in time, ideally before next LTS, we need to invert this:
  # Have the new APT output in the full test, using latest releases, and a subset for the
  # old output.
  @uses.config.contract_token
  Scenario Outline: APT News
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    When I remove support for `backports` in APT
    When I apt upgrade including phased updates
    When I apt autoremove
    When I apt install `jq`
    When I run `pro detach --assume-yes` with sudo
    # We are doing this because ESM pin might prevent some packages to be upgraded (i.e.
    # distro-info-data)
    When I apt dist-upgrade
    Given a `focal` `<machine_type>` machine named `apt-news-server`
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
    # Plucky shows the Calculating upgrade line more than once.
    # TODO: change those tests to have different output per release.
    Then stdout matches regexp:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      (Calculating upgrade...\n)+#
      # one
      #
      Summary:
        Upgrading: 0, Installing: 0, Removing: 0, Not Upgrading: 0
      """
    When I run shell command `pro api u.apt_news.current_news.v1 | jq .data.attributes.current_news` as non-root
    Then I will see the following on stdout:
      """
      "one"
      """
    # Test that it is not shown in apt-get output
    When I apt-get upgrade
    Then stdout matches regexp:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      (Calculating upgrade...\n)+0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
      """

    Examples: ubuntu release
      | release  | machine_type  |
      | plucky   | lxd-container |
      | plucky   | lxd-vm        |
      | questing | lxd-container |
      | questing | lxd-vm        |

  Scenario Outline: Cloud and series-specific URLs
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I apt install `ansible`
    # Update after installing to make sure messages are there
    When I apt update
    When I wait `30` seconds
    When I apt upgrade on a dry run
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
  Scenario Outline: APT news selectors
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I remove support for `backports` in APT
    When I attach `contract_token` with sudo
    When I apt upgrade including phased updates
    When I apt autoremove
    When I apt install `jq`
    When I run `pro detach --assume-yes` with sudo
    # We are doing this because ESM pin might prevent some packages to be upgraded (i.e.
    # distro-info-data)
    When I apt upgrade
    Given a `jammy` `<machine_type>` machine named `apt-news-server`
    When I apt install `nginx` on the `apt-news-server` machine
    When I run `sed -i "s/gzip on;/gzip on;\n\tgzip_min_length 1;\n\tgzip_types application\/json;\n/" /etc/nginx/nginx.conf` `with sudo` on the `apt-news-server` machine
    When I run `systemctl restart nginx` `with sudo` on the `apt-news-server` machine
    When I run `pro config set apt_news_url=http://$behave_var{machine-ip apt-news-server}/aptnews.json` with sudo
    # Testing codename selector
    When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
      """
      {
        "messages": [
          {
            "begin": "$behave_var{today}",
            "selectors": {
              "codenames": ["<wrong_release>"],
            },
            "lines": [
              "one"
            ]
          }
        ]
      }
      """
    When I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    When I run `systemctl start apt-news.service` with sudo
    When I wait `5` seconds
    When I apt upgrade
    Then I will see the following on stdout:
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
            "selectors": {
              "codenames": ["<release>"]
            },
            "lines": [
              "one",
              "two"
            ]
          }
        ]
      }
      """
    When I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    When I run `systemctl start apt-news.service` with sudo
    When I wait `5` seconds
    When I apt upgrade
    Then I will see the following on stdout:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      Calculating upgrade...
      #
      # one
      # two
      #
      0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
      """
    # Testing architectures selector
    When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
      """
      {
        "messages": [
          {
            "begin": "$behave_var{today}",
            "selectors": {
              "architectures": ["amd64"]
            },
            "lines": [
              "one",
              "two"
            ]
          }
        ]
      }
      """
    When I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    When I run `systemctl start apt-news.service` with sudo
    When I wait `5` seconds
    When I apt upgrade
    Then I will see the following on stdout:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      Calculating upgrade...
      #
      # one
      # two
      #
      0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
      """
    When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
      """
      {
        "messages": [
          {
            "begin": "$behave_var{today}",
            "selectors": {
              "architectures": ["arm64"]
            },
            "lines": [
              "one",
              "two"
            ]
          }
        ]
      }
      """
    When I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    When I run `systemctl start apt-news.service` with sudo
    When I wait `5` seconds
    When I apt upgrade
    Then I will see the following on stdout:
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
            "selectors": {
              "architectures": ["arm64", "amd64"]
            },
            "lines": [
              "one",
              "two"
            ]
          }
        ]
      }
      """
    When I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    When I run `systemctl start apt-news.service` with sudo
    When I wait `5` seconds
    When I apt upgrade
    Then I will see the following on stdout:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      Calculating upgrade...
      #
      # one
      # two
      #
      0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
      """
    # Testing packages selector when package is not installed
    When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
      """
      {
        "messages": [
          {
            "begin": "$behave_var{today}",
            "selectors": {
              "codenames": ["<release>"],
              "architectures": ["amd64"],
              "packages": [["libcurl4", "==", "<installed_version>"]]
            },
            "lines": [
              "one",
              "two"
            ]
          }
        ]
      }
      """
    When I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    When I run `systemctl start apt-news.service` with sudo
    When I wait `5` seconds
    And I apt upgrade
    Then I will see the following on stdout:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      Calculating upgrade...
      0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
      """
    # Testing package selector when package installed
    When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
      """
      {
        "messages": [
          {
            "begin": "$behave_var{today}",
            "selectors": {
              "packages": [["<package>", "==", "<installed_version>"]]
            },
            "lines": [
              "one",
              "two"
            ]
          }
        ]
      }
      """
    And I apt install `<package>=<installed_version>`
    And I run `apt-mark hold <package>` with sudo
    When I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    When I run `systemctl start apt-news.service` with sudo
    When I wait `5` seconds
    And I apt upgrade
    Then stdout contains substring:
      """
      #
      # one
      # two
      #
      """
    When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
      """
      {
        "messages": [
          {
            "begin": "$behave_var{today}",
            "selectors": {
              "packages": [["<package>", "<", "9.0.0"]]
            },
            "lines": [
              "one",
              "two"
            ]
          }
        ]
      }
      """
    When I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    When I run `systemctl start apt-news.service` with sudo
    When I wait `5` seconds
    And I apt upgrade
    Then stdout contains substring:
      """
      #
      # one
      # two
      #
      """
    When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
      """
      {
        "messages": [
          {
            "begin": "$behave_var{today}",
            "selectors": {
              "codenames": ["<release>"],
              "architectures": ["amd64"],
              "packages": [["<package>", "==", "<installed_version>"]]
            },
            "lines": [
              "one",
              "two"
            ]
          }
        ]
      }
      """
    When I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    When I run `systemctl start apt-news.service` with sudo
    When I wait `5` seconds
    And I apt upgrade
    Then stdout contains substring:
      """
      #
      # one
      # two
      #
      """
    # Still displayed if one package selector fails
    When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
      """
      {
        "messages": [
          {
            "begin": "$behave_var{today}",
            "selectors": {
              "packages": [
                  ["<package>", "==", "<installed_version>"],
                  ["linux", "<", "1"]
              ]
            },
            "lines": [
              "one",
              "two"
            ]
          }
        ]
      }
      """
    When I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    When I run `systemctl start apt-news.service` with sudo
    When I wait `5` seconds
    And I apt upgrade
    Then stdout contains substring:
      """
      #
      # one
      # two
      #
      """
    # Testing multiple selectors together
    When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
      """
      {
        "messages": [
          {
            "begin": "$behave_var{today}",
            "selectors": {
              "codenames": ["<wrong_release>"],
              "architectures": ["arm64"],
              "packages": [["<package>", "==", "<installed_version>"]]
            },
            "lines": [
              "one",
              "two"
            ]
          }
        ]
      }
      """
    And I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    And I run `systemctl start apt-news.service` with sudo
    And I wait `5` seconds
    And I apt upgrade
    Then I will see the following on stdout:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      Calculating upgrade...
      The following packages have been kept back:
        <package>
      0 upgraded, 0 newly installed, 0 to remove and 1 not upgraded.
      """
    When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
      """
      {
        "messages": [
          {
            "begin": "$behave_var{today}",
            "selectors": {
              "codenames": ["<release>"],
              "architectures": ["amd64"],
              "packages": [["<package>", ">", "<installed_version>"]]
            },
            "lines": [
              "one",
              "two"
            ]
          }
        ]
      }
      """
    And I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    And I run `systemctl start apt-news.service` with sudo
    And I wait `5` seconds
    And I apt upgrade
    Then I will see the following on stdout:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      Calculating upgrade...
      The following packages have been kept back:
        <package>
      0 upgraded, 0 newly installed, 0 to remove and 1 not upgraded.
      """

    Examples: ubuntu release
      | release | machine_type  | wrong_release | package         | installed_version |
      | xenial  | lxd-container | bionic        | libcurl3-gnutls | 7.47.0-1ubuntu2   |
      | bionic  | lxd-container | focal         | xz-utils        | 5.2.2-1.3         |
      | focal   | lxd-container | bionic        | libcurl4        | 7.68.0-1ubuntu2   |
      | jammy   | lxd-container | focal         | libcurl4        | 7.81.0-1          |
      | noble   | lxd-container | jammy         | libcurl4t64     | 8.5.0-2ubuntu10   |

  @uses.config.contract_token
  Scenario Outline: APT news selectors
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I remove support for `backports` in APT
    When I attach `contract_token` with sudo
    When I apt upgrade including phased updates
    When I apt autoremove
    When I apt install `jq`
    When I run `pro detach --assume-yes` with sudo
    # We are doing this because ESM pin might prevent some packages to be upgraded (i.e.
    # distro-info-data)
    When I apt upgrade
    Given a `jammy` `<machine_type>` machine named `apt-news-server`
    When I apt install `nginx` on the `apt-news-server` machine
    When I run `sed -i "s/gzip on;/gzip on;\n\tgzip_min_length 1;\n\tgzip_types application\/json;\n/" /etc/nginx/nginx.conf` `with sudo` on the `apt-news-server` machine
    When I run `systemctl restart nginx` `with sudo` on the `apt-news-server` machine
    When I run `pro config set apt_news_url=http://$behave_var{machine-ip apt-news-server}/aptnews.json` with sudo
    # Testing codename selector
    When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
      """
      {
        "messages": [
          {
            "begin": "$behave_var{today}",
            "selectors": {
              "codenames": ["<wrong_release>"],
            },
            "lines": [
              "one"
            ]
          }
        ]
      }
      """
    When I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    When I run `systemctl start apt-news.service` with sudo
    When I wait `5` seconds
    When I apt upgrade
    Then stdout matches regexp:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      (Calculating upgrade...\n)+Summary:
        Upgrading: 0, Installing: 0, Removing: 0, Not Upgrading: 0
      """
    When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
      """
      {
        "messages": [
          {
            "begin": "$behave_var{today}",
            "selectors": {
              "codenames": ["<release>"]
            },
            "lines": [
              "one",
              "two"
            ]
          }
        ]
      }
      """
    When I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    When I run `systemctl start apt-news.service` with sudo
    When I wait `5` seconds
    When I apt upgrade
    Then stdout matches regexp:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      (Calculating upgrade...\n)+#
      # one
      # two
      #
      Summary:
        Upgrading: 0, Installing: 0, Removing: 0, Not Upgrading: 0
      """
    # Testing architectures selector
    When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
      """
      {
        "messages": [
          {
            "begin": "$behave_var{today}",
            "selectors": {
              "architectures": ["amd64"]
            },
            "lines": [
              "one",
              "two"
            ]
          }
        ]
      }
      """
    When I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    When I run `systemctl start apt-news.service` with sudo
    When I wait `5` seconds
    When I apt upgrade
    Then stdout matches regexp:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      (Calculating upgrade...\n)+#
      # one
      # two
      #
      Summary:
        Upgrading: 0, Installing: 0, Removing: 0, Not Upgrading: 0
      """
    When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
      """
      {
        "messages": [
          {
            "begin": "$behave_var{today}",
            "selectors": {
              "architectures": ["arm64"]
            },
            "lines": [
              "one",
              "two"
            ]
          }
        ]
      }
      """
    When I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    When I run `systemctl start apt-news.service` with sudo
    When I wait `5` seconds
    When I apt upgrade
    Then stdout matches regexp:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      (Calculating upgrade...\n)+Summary:
        Upgrading: 0, Installing: 0, Removing: 0, Not Upgrading: 0
      """
    When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
      """
      {
        "messages": [
          {
            "begin": "$behave_var{today}",
            "selectors": {
              "architectures": ["arm64", "amd64"]
            },
            "lines": [
              "one",
              "two"
            ]
          }
        ]
      }
      """
    When I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    When I run `systemctl start apt-news.service` with sudo
    When I wait `5` seconds
    When I apt upgrade
    Then stdout matches regexp:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      (Calculating upgrade...\n)+#
      # one
      # two
      #
      Summary:
        Upgrading: 0, Installing: 0, Removing: 0, Not Upgrading: 0
      """
    # Testing packages selector when package is not installed
    When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
      """
      {
        "messages": [
          {
            "begin": "$behave_var{today}",
            "selectors": {
              "codenames": ["<release>"],
              "architectures": ["amd64"],
              "packages": [["libcurl4", "==", "<installed_version>"]]
            },
            "lines": [
              "one",
              "two"
            ]
          }
        ]
      }
      """
    When I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    When I run `systemctl start apt-news.service` with sudo
    When I wait `5` seconds
    And I apt upgrade
    Then stdout matches regexp:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      (Calculating upgrade...\n)+Summary:
        Upgrading: 0, Installing: 0, Removing: 0, Not Upgrading: 0
      """
    # Testing package selector when package installed
    When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
      """
      {
        "messages": [
          {
            "begin": "$behave_var{today}",
            "selectors": {
              "packages": [["<package>", "==", "<installed_version>"]]
            },
            "lines": [
              "one",
              "two"
            ]
          }
        ]
      }
      """
    And I apt install `<package>=<installed_version>`
    And I run `apt-mark hold <package>` with sudo
    When I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    When I run `systemctl start apt-news.service` with sudo
    When I wait `5` seconds
    And I apt upgrade
    Then stdout contains substring:
      """
      #
      # one
      # two
      #
      """
    When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
      """
      {
        "messages": [
          {
            "begin": "$behave_var{today}",
            "selectors": {
              "packages": [["<package>", "<", "9.0.0"]]
            },
            "lines": [
              "one",
              "two"
            ]
          }
        ]
      }
      """
    When I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    When I run `systemctl start apt-news.service` with sudo
    When I wait `5` seconds
    And I apt upgrade
    Then stdout contains substring:
      """
      #
      # one
      # two
      #
      """
    When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
      """
      {
        "messages": [
          {
            "begin": "$behave_var{today}",
            "selectors": {
              "codenames": ["<release>"],
              "architectures": ["amd64"],
              "packages": [["<package>", "==", "<installed_version>"]]
            },
            "lines": [
              "one",
              "two"
            ]
          }
        ]
      }
      """
    When I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    When I run `systemctl start apt-news.service` with sudo
    When I wait `5` seconds
    And I apt upgrade
    Then stdout contains substring:
      """
      #
      # one
      # two
      #
      """
    # Still displayed if one package selector fails
    When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
      """
      {
        "messages": [
          {
            "begin": "$behave_var{today}",
            "selectors": {
              "packages": [
                  ["<package>", "==", "<installed_version>"],
                  ["linux", "<", "1"]
              ]
            },
            "lines": [
              "one",
              "two"
            ]
          }
        ]
      }
      """
    When I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    When I run `systemctl start apt-news.service` with sudo
    When I wait `5` seconds
    And I apt upgrade
    Then stdout contains substring:
      """
      #
      # one
      # two
      #
      """
    # Testing multiple selectors together
    When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
      """
      {
        "messages": [
          {
            "begin": "$behave_var{today}",
            "selectors": {
              "codenames": ["<wrong_release>"],
              "architectures": ["arm64"],
              "packages": [["<package>", "==", "<installed_version>"]]
            },
            "lines": [
              "one",
              "two"
            ]
          }
        ]
      }
      """
    And I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    And I run `systemctl start apt-news.service` with sudo
    And I wait `5` seconds
    And I apt upgrade
    Then stdout matches regexp:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      (Calculating upgrade...\n)+Not upgrading:
        <package>

      Summary:
        Upgrading: 0, Installing: 0, Removing: 0, Not Upgrading: 1
      """
    When I create the file `/var/www/html/aptnews.json` on the `apt-news-server` machine with the following:
      """
      {
        "messages": [
          {
            "begin": "$behave_var{today}",
            "selectors": {
              "codenames": ["<release>"],
              "architectures": ["amd64"],
              "packages": [["<package>", ">", "<installed_version>"]]
            },
            "lines": [
              "one",
              "two"
            ]
          }
        ]
      }
      """
    And I run `rm -rf /var/lib/apt/periodic/update-success-stamp` with sudo
    And I run `systemctl start apt-news.service` with sudo
    And I wait `5` seconds
    And I apt upgrade
    Then stdout matches regexp:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      (Calculating upgrade...\n)+Not upgrading:
        <package>

      Summary:
        Upgrading: 0, Installing: 0, Removing: 0, Not Upgrading: 1
      """

    Examples: ubuntu release
      | release | machine_type  | wrong_release | package   | installed_version |
      | plucky  | lxd-container | jammy         | pyzfs-doc | 2.3.1-1ubuntu1    |

  Scenario Outline: APT Hook does not error when run as non-root
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `apt upgrade --simulate` as non-root
    Then I will see the following on stderr:
      """
      WARNING: apt does not have a stable CLI interface. Use with caution in scripts.
      """

    Examples: ubuntu release
      | release  | machine_type  |
      | xenial   | lxd-container |
      | bionic   | lxd-container |
      | focal    | lxd-container |
      | jammy    | lxd-container |
      | noble    | lxd-container |
      | plucky   | lxd-container |
      | questing | lxd-container |

  @uses.config.contract_token
  Scenario Outline: APT Hook do not advertises esm-apps on upgrade for interim releases
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I apt upgrade including phased updates
    And I apt dist-upgrade
    And I apt autoremove
    And I apt install `hello`
    And I run `pro config set apt_news=false` with sudo
    And I run `pro refresh messages` with sudo
    And I apt upgrade
    Then stdout does not match regexp:
      """
      Get more security updates through Ubuntu Pro with 'esm-apps' enabled:
      """
    When I apt-get upgrade
    Then stdout matches regexp:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      (Calculating upgrade...\n)+0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
      """
    When I attach `contract_token` with sudo
    When I apt upgrade on a dry run
    Then stdout matches regexp:
      """
      Reading package lists...
      Building dependency tree...
      Reading state information...
      (Calculating upgrade...\n)+Summary:
        Upgrading: 0, Installing: 0, Removing: 0, Not Upgrading: 0
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
      (Calculating upgrade...\n)+Summary:
        Upgrading: 0, Installing: 0, Removing: 0, Not Upgrading: 0
      """

    Examples: ubuntu release
      | release  | machine_type  |
      | plucky   | lxd-container |
      | questing | lxd-container |
