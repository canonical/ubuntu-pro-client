@uses.config.contract_token
Feature: Command behaviour when attached to an UA subscription

    @series.all
    Scenario Outline: Attached refresh in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua refresh` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\)
            """
        When I run `ua refresh` with sudo
        Then I will see the following on stdout:
            """
            Successfully refreshed your subscription
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | trusty  |
           | xenial  |

    @series.all
    Scenario Outline: Attached disable of an already disabled service in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua disable livepatch` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\)
            """
        And I verify that running `ua disable livepatch` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            Livepatch is not currently enabled
            See: sudo ua status
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | trusty  |
           | xenial  |

    @series.all
    Scenario Outline: Attached disable of a service in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua disable foobar` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\)
            """
        And I verify that running `ua disable foobar` `with sudo` exits `1`
        And stderr matches regexp:
            """
            Cannot disable unknown service 'foobar'.
            Try cc-eal, cis, esm-apps, esm-infra, fips, fips-updates, livepatch
            """
        And I verify that running `ua disable esm-infra` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\)
            """
        When I run `ua disable esm-infra` with sudo
        Then I will see the following on stdout:
            """
            Updating package lists
            """
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            esm-infra    +yes      +disabled +UA Infra: Extended Security Maintenance \(ESM\)
            """
        And I verify that running `apt update` `with sudo` exits `0`

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | xenial  |

    @series.all
    Scenario Outline: Attached detach in a trusty machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua detach` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\)
            """
        When I run `ua detach --assume-yes` with sudo
        Then I will see the following on stdout:
            """
            Detach will disable the following service:
                esm-infra
            Updating package lists
            This machine is now detached
            """
       When I run `ua status --all` as non-root
       Then stdout matches regexp:
           """
           SERVICE       AVAILABLE  DESCRIPTION
           cc-eal        +<cc-eal>   +Common Criteria EAL2 Provisioning Packages
           cis           +<cis>      +Center for Internet Security Audit Tools
           esm-apps      +<esm-apps> +UA Apps: Extended Security Maintenance \(ESM\)
           esm-infra     +yes        +UA Infra: Extended Security Maintenance \(ESM\)
           fips          +<fips>     +NIST-certified FIPS modules
           fips-updates  +<fips>     +Uncertified security updates to FIPS modules
           livepatch     +yes        +Canonical Livepatch service
           """
       And stdout matches regexp:
          """
          This machine is not attached to a UA subscription.
          """
       And I verify that running `apt update` `with sudo` exits `0`

       Examples: ubuntu release
           | release | esm-apps | cc-eal | cis | fips | fips-update |
           | bionic  | yes      | no     | yes | yes  | yes         |
           | focal   | yes      | no     | no  | no   | no          |
           | trusty  | no       | no     | no  | no   | no          |
           | xenial  | yes      | yes    | yes | yes  | yes         |

    @series.all
    Scenario Outline: Attached auto-attach in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua auto-attach` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\)
            """
        When I run `ua auto-attach` with sudo
        Then stderr matches regexp:
            """
            This machine is already attached
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | trusty  |
           | xenial  |

    @series.all
    Scenario Outline: Attached show version in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua version` as non-root
        Then I will see the uaclient version on stdout
        When I run `ua version` with sudo
        Then I will see the uaclient version on stdout
        When I run `ua --version` as non-root
        Then I will see the uaclient version on stdout
        When I run `ua --version` with sudo
        Then I will see the uaclient version on stdout

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | trusty  |
           | xenial  |

    @series.all
    Scenario Outline: Unattached status in a ubuntu machine with feature overrides
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I create the file `/tmp/machine-token-overlay.json` with the following:
        """
        {
            "machineTokenInfo": {
                "contractInfo": {
                    "resourceEntitlements": [
                        {
                            "type": "cc-eal",
                            "entitled": false
                        }
                    ]
                }
            }
        }
        """
        And I append the following on uaclient config:
        """
        features:
          machine_token_overlay: "/tmp/machine-token-overlay.json"
          disable_auto_attach: true
          other: false
        """
        And I attach `contract_token` with sudo
        And I run `ua status --all` with sudo
        Then stdout matches regexp:
            """
            SERVICE       ENTITLED  STATUS    DESCRIPTION
            cc-eal        no
            """
        When I run `ua --version` as non-root
        Then I will see the uaclient version on stdout with features ` +disable_auto_attach +machine_token_overlay -other`
        When I run `ua version` as non-root
        Then I will see the uaclient version on stdout with features ` +disable_auto_attach +machine_token_overlay -other`
        When I run `ua auto-attach` with sudo
        Then stdout matches regexp:
        """
        Skipping auto-attach. Config disable_auto_attach is set.
        """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | trusty  |
           | xenial  |

    @series.all
    Scenario Outline: Attached disable of different services in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua disable esm-infra livepatch foobar` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\)
            """
        And I verify that running `ua disable esm-infra livepatch foobar` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            Updating package lists
            Livepatch is not currently enabled
            See: sudo ua status
            """
        And stderr matches regexp:
            """
            Cannot disable unknown service 'foobar'.
            Try cc-eal, cis, esm-apps, esm-infra, fips, fips-updates, livepatch
            """
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            esm-infra    +yes      +disabled +UA Infra: Extended Security Maintenance \(ESM\)
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | trusty  |
           | xenial  |

    @series.trusty
    Scenario: Attached disable of an already enabled service in a trusty machine
        Given a `trusty` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua disable foobar` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\)
            """
        And I verify that running `ua disable foobar` `with sudo` exits `1`
        And stderr matches regexp:
            """
            Cannot disable unknown service 'foobar'.
            Try cc-eal, cis, esm-apps, esm-infra, fips, fips-updates, livepatch
            """
        And I verify that running `ua disable esm-infra` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\)
            """
        When I run `ua disable esm-infra` with sudo
        Then I will see the following on stdout:
            """
            Updating package lists
            """
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            esm-infra    +yes      +disabled +UA Infra: Extended Security Maintenance \(ESM\)
            """
        And I verify that running `apt update` `with sudo` exits `0`
        When I run `apt-cache policy` with sudo
        Then apt-cache policy for the following url has permission `-32768`
        """
        https://esm.ubuntu.com/ubuntu/ trusty-infra-security/main amd64 Packages
        """
        And apt-cache policy for the following url has permission `-32768`
        """
        https://esm.ubuntu.com/ubuntu/ trusty-infra-updates/main amd64 Packages
        """

    @series.all
    Scenario Outline: Help command on an attached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua help esm-infra` with sudo
        Then I will see the following on stdout:
            """
            Name:
            esm-infra

            Entitled:
            yes

            Status:
            enabled

            Help:
            esm-infra provides access to a private ppa which includes available high
            and critical CVE fixes for Ubuntu LTS packages in the Ubuntu Main
            repository between the end of the standard Ubuntu LTS security
            maintenance and its end of life. It is enabled by default with
            Extended Security Maintenance (ESM) for UA Apps and UA Infra.
            You can find our more about the esm service at
            https://ubuntu.com/security/esm
            """
        When I run `ua help esm-infra --format json` with sudo
        Then I will see the following on stdout:
            """
            {"name": "esm-infra", "entitled": "yes", "status": "enabled", "help": "esm-infra provides access to a private ppa which includes available high\nand critical CVE fixes for Ubuntu LTS packages in the Ubuntu Main\nrepository between the end of the standard Ubuntu LTS security\nmaintenance and its end of life. It is enabled by default with\nExtended Security Maintenance (ESM) for UA Apps and UA Infra.\nYou can find our more about the esm service at\nhttps://ubuntu.com/security/esm\n"}
            """
        And I verify that running `ua help invalid-service` `with sudo` exits `1`
        And I will see the following on stderr:
            """
            No help available for 'invalid-service'
            """
        When I run `ua --help` as non-root
        Then stdout matches regexp:
        """
        Client to manage Ubuntu Advantage services on a machine.
         - esm-infra: UA Infra: Extended Security Maintenance \(ESM\)
           \(https://ubuntu.com/security/esm\)
         - fips-updates: Uncertified security updates to FIPS modules
           \(https://ubuntu.com/security/certifications#fips\)
         - fips: NIST-certified FIPS modules
           \(https://ubuntu.com/security/certifications#fips\)
         - livepatch: Canonical Livepatch service
           \(https://ubuntu.com/security/livepatch\)
        """
        When I run `ua help` as non-root
        Then stdout matches regexp:
        """
        Client to manage Ubuntu Advantage services on a machine.
         - esm-infra: UA Infra: Extended Security Maintenance \(ESM\)
           \(https://ubuntu.com/security/esm\)
         - fips-updates: Uncertified security updates to FIPS modules
           \(https://ubuntu.com/security/certifications#fips\)
         - fips: NIST-certified FIPS modules
           \(https://ubuntu.com/security/certifications#fips\)
         - livepatch: Canonical Livepatch service
           \(https://ubuntu.com/security/livepatch\)
        """
        When I run `ua help --all` as non-root
        Then stdout matches regexp:
        """
        Client to manage Ubuntu Advantage services on a machine.
         - cc-eal: Common Criteria EAL2 Provisioning Packages
           \(https://ubuntu.com/cc-eal\)
         - cis: Center for Internet Security Audit Tools
           \(https://ubuntu.com/security/certifications#cis\)
         - esm-apps: UA Apps: Extended Security Maintenance \(ESM\)
           \(https://ubuntu.com/security/esm\)
         - esm-infra: UA Infra: Extended Security Maintenance \(ESM\)
           \(https://ubuntu.com/security/esm\)
         - fips-updates: Uncertified security updates to FIPS modules
           \(https://ubuntu.com/security/certifications#fips\)
         - fips: NIST-certified FIPS modules
           \(https://ubuntu.com/security/certifications#fips\)
         - livepatch: Canonical Livepatch service
           \(https://ubuntu.com/security/livepatch\)
        """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | trusty  |
           | xenial  |

    @series.all
    Scenario Outline: Purge package after attaching it to a machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `touch /etc/apt/preferences.d/ubuntu-esm-infra` with sudo
        Then I verify that files exist matching `/var/log/ubuntu-advantage.log`
        And I verify that running `test -d /var/lib/ubuntu-advantage` `with sudo` exits `0`
        And I verify that files exist matching `/etc/apt/auth.conf.d/90ubuntu-advantage`
        And I verify that files exist matching `/etc/apt/trusted.gpg.d/ubuntu-advantage-esm-infra-trusty.gpg`
        And I verify that files exist matching `/etc/apt/sources.list.d/ubuntu-esm-infra.list`
        And I verify that files exist matching `/etc/apt/preferences.d/ubuntu-esm-infra`
        When I run `apt-get purge ubuntu-advantage-tools -y` with sudo
        Then stdout matches regexp:
        """
        Purging configuration files for ubuntu-advantage-tools
        """
        And I verify that no files exist matching `/var/log/ubuntu-advantage.log`
        And I verify that no files exist matching `/var/lib/ubuntu-advantage`
        And I verify that no files exist matching `/etc/apt/auth.conf.d/90ubuntu-advantage`
        And I verify that no files exist matching `/etc/apt/sources.list.d/ubuntu-*`
        And I verify that no files exist matching `/etc/apt/trusted.gpg.d/ubuntu-advantage-*`
        And I verify that no files exist matching `/etc/apt/preferences.d/ubuntu-*`

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | trusty  |
           | xenial  |

    @series.all
    Scenario Outline: Enable command with invalid repositories in user machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua disable esm-infra` with sudo
        And I run `add-apt-repository ppa:ua-client/staging -y` with sudo
        And I run `apt update` with sudo
        And I run `sed -i 's/ubuntu/ubun/' /etc/apt/sources.list.d/<ppa_file>.list` with sudo
        And I run `ua enable esm-infra` with sudo
        Then stdout matches regexp:
        """
        One moment, checking your subscription first
        Updating package lists
        APT update failed.
        APT update failed to read APT config for the following URL:
        - http://ppa.launchpad.net/ua-client/staging/ubun
        """

        Examples: ubuntu release
           | release | ppa_file                        |
           | trusty  | ua-client-staging-trusty        |
           | xenial  | ua-client-ubuntu-staging-xenial |
           | bionic  | ua-client-ubuntu-staging-bionic |
           | focal   | ua-client-ubuntu-staging-focal  |
