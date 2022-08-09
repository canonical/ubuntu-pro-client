Feature: MOTD Messages

    @series.xenial
    @uses.config.machine_type.lxd.container
    Scenario Outline: MOTD Messages for EOL release
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get install -y update-motd` with sudo
        When I run `pro refresh messages` with sudo
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout matches regexp:
        """
         \* Documentation:  https:\/\/help\.ubuntu\.com
         \* Management:     https:\/\/landscape\.canonical\.com
         \* Support:        https:\/\/ubuntu\.com\/advantage

         \* Introducing Extended Security Maintenance for Applications\.
           Receive updates to over 30,000 software packages with your
           Ubuntu Pro subscription\. Free for personal use\.

             https:\/\/ubuntu.com\/16-04

        \w+
        """
        When I attach `contract_token` with sudo
        And I run `update-motd` with sudo
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout matches regexp:
        """
         \* Documentation:  https:\/\/help\.ubuntu\.com
         \* Management:     https:\/\/landscape\.canonical\.com
         \* Support:        https:\/\/ubuntu\.com\/advantage

        \w+
        """
        Examples: ubuntu release
           | release |
           | xenial  |

    @series.xenial
    @series.bionic
    @uses.config.machine_type.aws.pro
    Scenario Outline: MOTD Messages for EOL release
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get install -y update-motd` with sudo
        When I run `pro refresh messages` with sudo
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout matches regexp:
        """
         \* Introducing Extended Security Maintenance for Applications\.
           Receive updates to over 30,000 software packages with your
           Ubuntu Pro subscription\. Free for personal use\.

             <url>
        """
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        When I run `pro auto-attach` with sudo
        And I run `update-motd` with sudo
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout does not match regexp:
        """
         \* Introducing Extended Security Maintenance for Applications\.
           Receive updates to over 30,000 software packages with your
           Ubuntu Pro subscription\. Free for personal use\.

             <url>
        """
        Examples: ubuntu release
           | release | url                            |
           | xenial  | https:\/\/ubuntu.com\/16-04    |
           | bionic  | https:\/\/ubuntu.com\/aws\/pro |

    @series.xenial
    @series.bionic
    @uses.config.machine_type.azure.pro
    Scenario Outline: MOTD Messages for EOL release
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get install -y update-motd` with sudo
        When I run `pro refresh messages` with sudo
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout matches regexp:
        """
         \* Introducing Extended Security Maintenance for Applications\.
           Receive updates to over 30,000 software packages with your
           Ubuntu Pro subscription\. Free for personal use\.

             <url>
        """
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        When I run `pro auto-attach` with sudo
        And I run `update-motd` with sudo
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout does not match regexp:
        """
         \* Introducing Extended Security Maintenance for Applications\.
           Receive updates to over 30,000 software packages with your
           Ubuntu Pro subscription\. Free for personal use\.

             <url>
        """
        Examples: ubuntu release
           | release | url                                |
           | xenial  | https:\/\/ubuntu.com\/16-04\/azure |
           | bionic  | https:\/\/ubuntu.com\/azure\/pro   |

    @series.xenial
    @series.bionic
    @uses.config.machine_type.gcp.pro
    Scenario Outline: MOTD Messages for EOL release
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get install -y update-motd` with sudo
        When I run `pro refresh messages` with sudo
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout matches regexp:
        """
         \* Introducing Extended Security Maintenance for Applications\.
           Receive updates to over 30,000 software packages with your
           Ubuntu Pro subscription\. Free for personal use\.

             <url>
        """
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        When I run `pro auto-attach` with sudo
        And I run `update-motd` with sudo
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout does not match regexp:
        """
         \* Introducing Extended Security Maintenance for Applications\.
           Receive updates to over 30,000 software packages with your
           Ubuntu Pro subscription\. Free for personal use\.

             <url>
        """
        Examples: ubuntu release
           | release | url                            |
           | xenial  | https:\/\/ubuntu.com\/16-04    |
           | bionic  | https:\/\/ubuntu.com\/gcp\/pro |
