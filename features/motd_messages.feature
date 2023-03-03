Feature: MOTD Messages

    @series.xenial
    @series.bionic
    @uses.config.machine_type.lxd.container
    Scenario Outline: MOTD Announce Message
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get install -y update-motd` with sudo
        When I run `pro refresh messages` with sudo
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout matches regexp:
        """

         \* Introducing Expanded Security Maintenance for Applications\.
           Receive updates to over 25,000 software packages with your
           Ubuntu Pro subscription\. Free for personal use\.

             <url>

        [\w\d]+
        """
        When I attach `contract_token` with sudo
        And I run `update-motd` with sudo
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout does not match regexp:
        """
         \* Introducing Expanded Security Maintenance for Applications\.
           Receive updates to over 25,000 software packages with your
           Ubuntu Pro subscription\. Free for personal use\.

             <url>
        """
        Examples: ubuntu release
           | release | url                         |
           | xenial  | https:\/\/ubuntu.com\/16-04 |
           | bionic  | https:\/\/ubuntu.com\/pro   |

    @series.xenial
    @series.bionic
    @uses.config.machine_type.aws.generic
    Scenario Outline: AWS URLs
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get install -y update-motd` with sudo
        When I run `pro refresh messages` with sudo
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout matches regexp:
        """
         \* Introducing Expanded Security Maintenance for Applications\.
           Receive updates to over 25,000 software packages with your
           Ubuntu Pro subscription\. Free for personal use\.

             <url>
        """
        Examples: ubuntu release
           | release | url                            |
           | xenial  | https:\/\/ubuntu.com\/16-04    |
           | bionic  | https:\/\/ubuntu.com\/aws\/pro |

    @series.xenial
    @series.bionic
    @uses.config.machine_type.azure.generic
    Scenario Outline: Azure URLs
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get install -y update-motd` with sudo
        When I run `pro refresh messages` with sudo
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout matches regexp:
        """
         \* Introducing Expanded Security Maintenance for Applications\.
           Receive updates to over 25,000 software packages with your
           Ubuntu Pro subscription\. Free for personal use\.

             <url>
        """
        Examples: ubuntu release
           | release | url                                |
           | xenial  | https:\/\/ubuntu.com\/16-04\/azure |
           | bionic  | https:\/\/ubuntu.com\/azure\/pro   |

    @series.xenial
    @series.bionic
    @uses.config.machine_type.gcp.generic
    Scenario Outline: GCP URLs
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get install -y update-motd` with sudo
        When I run `pro refresh messages` with sudo
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout matches regexp:
        """
         \* Introducing Expanded Security Maintenance for Applications\.
           Receive updates to over 25,000 software packages with your
           Ubuntu Pro subscription\. Free for personal use\.

             <url>
        """
        Examples: ubuntu release
           | release | url                            |
           | xenial  | https:\/\/ubuntu.com\/16-04    |
           | bionic  | https:\/\/ubuntu.com\/gcp\/pro |

    @series.xenial
    @series.bionic
    @uses.config.machine_type.lxd.container
    Scenario Outline: MOTD Contract Expiration Notices After Contract Update
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get update` with sudo
        When I attach `contract_token` with sudo
        When I update contract to use `effectiveTo` as `$behave_var{today +2}`
        When I run `pro refresh messages` with sudo
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout does not match regexp:
        """
        [\w\d.]+

        CAUTION: Your Ubuntu Pro subscription will expire in 2 days.
        Renew your subscription at https:\/\/ubuntu.com\/pro to ensure continued security
        coverage for your applications.

        [\w\d.]+
        """
        When I update contract to use `effectiveTo` as `$behave_var{today -3}`
        When I wait `1` seconds
        When I run `pro refresh messages` with sudo
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout does not match regexp:
        """
        [\w\d.]+

        CAUTION: Your Ubuntu Pro subscription expired on \d+ \w+ \d+.
        Renew your subscription at https:\/\/ubuntu.com\/pro to ensure continued security
        coverage for your applications.
        Your grace period will expire in 11 days.

        [\w\d.]+
        """
        When I update contract to use `effectiveTo` as `$behave_var{today -20}`
        When I wait `1` seconds
        When I run `pro refresh messages` with sudo
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout does not match regexp:
        """
        [\w\d.]+

        \*Your Ubuntu Pro subscription has EXPIRED\*
        \d+ additional security update\(s\) require Ubuntu Pro with '<service>' enabled.
        Renew your service at https:\/\/ubuntu.com\/pro

        [\w\d.]+
        """
        When I run `apt-get upgrade -y` with sudo
        When I wait `1` seconds
        When I run `pro refresh messages` with sudo
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout does not match regexp:
        """
        [\w\d.]+

        \*Your Ubuntu Pro subscription has EXPIRED\*
        Renew your service at https:\/\/ubuntu.com\/pro

        [\w\d.]+
        """
        Examples: ubuntu release
           | release | service   |
           | xenial  | esm-infra |
           | bionic  | esm-apps  |


    @series.xenial
    @series.bionic
    @uses.config.machine_type.lxd.container
    Scenario Outline: MOTD Contract Expiration Notices with contract not updated
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get update` with sudo
        And I run `apt-get install ansible -y` with sudo
        And I attach `contract_token` with sudo
        And I create the file `/tmp/machine-token-overlay.json` with the following:
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
        And I wait `1` seconds
        And I run `pro refresh messages` with sudo
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout matches regexp:
        """
        [\w\d.]+

        CAUTION: Your Ubuntu Pro subscription will expire in 2 days.
        Renew your subscription at https:\/\/ubuntu.com\/pro to ensure continued security
        coverage for your applications.

        [\w\d.]+
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
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout matches regexp:
        """
        [\w\d.]+

        CAUTION: Your Ubuntu Pro subscription expired on \d+ \w+ \d+.
        Renew your subscription at https:\/\/ubuntu.com\/pro to ensure continued security
        coverage for your applications.
        Your grace period will expire in 11 days.

        [\w\d.]+
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
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout matches regexp:
        """
        [\w\d.]+

        \*Your Ubuntu Pro subscription has EXPIRED\*
        \d+ additional security update\(s\) require Ubuntu Pro with '<service>' enabled.
        Renew your service at https:\/\/ubuntu.com\/pro

        [\w\d.]+
        """
        When I run `apt-get upgrade -y` with sudo
        When I wait `1` seconds
        When I run `pro refresh messages` with sudo
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout matches regexp:
        """
        [\w\d.]+

        \*Your Ubuntu Pro subscription has EXPIRED\*
        Renew your service at https:\/\/ubuntu.com\/pro

        [\w\d.]+
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
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout matches regexp:
        """
        [\w\d.]+

        \*Your Ubuntu Pro subscription has EXPIRED\*
        Renew your service at https:\/\/ubuntu.com\/pro

        [\w\d.]+
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
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout matches regexp:
        """
        [\w\d.]+

        Your DGX contract entitles you to ESM updates.
        Please contact your NVIDIA account manager to get your Pro subscription.

        [\w\d.]+
        """
        Examples: ubuntu release
           | release | service   |
           | xenial  | esm-infra |
           | bionic  | esm-apps  |
