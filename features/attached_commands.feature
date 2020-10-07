@uses.config.contract_token
Feature: Command behaviour when attached to an UA subscription

    @series.all
    Scenario Outline: Attached refresh in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua refresh` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
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
        And I run `ua disable livepatch` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua disable livepatch` with sudo
        Then I will see the following on stdout:
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
    Scenario Outline: Attached disable of an unknown service in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua disable foobar` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua disable foobar` with sudo
        Then stderr matches regexp:
            """
            Cannot disable unknown service 'foobar'.
            Try cc-eal, cis-audit, esm-apps, esm-infra, fips, fips-updates, livepatch
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | trusty  |
           | xenial  |

    @series.all
    Scenario Outline: Attached detach in a trusty machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua detach` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
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
           esm-apps      +<esm-apps> +UA Apps: Extended Security Maintenance
           esm-infra     +yes        +UA Infra: Extended Security Maintenance
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
           | release | esm-apps | cc-eal | fips | fips-update |
           | bionic  | yes      | no     | yes  | yes         |
           | focal   | yes      | no     | no   | no          |
           | trusty  | no       | no     | no   | no          |
           | xenial  | yes      | yes    | yes  | yes         |

    @series.all
    Scenario Outline: Attached auto-attach in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua auto-attach` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
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
        And I run `ua disable esm-infra livepatch foobar` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua disable esm-infra livepatch foobar` with sudo
        Then I will see the following on stdout:
            """
            Updating package lists
            Livepatch is not currently enabled
            See: sudo ua status
            """
        And stderr matches regexp:
            """
            Cannot disable unknown service 'foobar'.
            Try cc-eal, cis-audit, esm-apps, esm-infra, fips, fips-updates, livepatch
            """
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            esm-infra    +yes      +disabled +UA Infra: Extended Security Maintenance
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | trusty  |
           | xenial  |

    @series.xenial
    @series.bionic
    @series.focal
    Scenario Outline: Attached disable of an already enabled service in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua disable esm-infra` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua disable esm-infra` with sudo
        Then I will see the following on stdout:
            """
            Updating package lists
            """
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            esm-infra    +yes      +disabled +UA Infra: Extended Security Maintenance
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | xenial  |

    @series.trusty
    Scenario: Attached disable of an already enabled service in a trusty machine
        Given a `trusty` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua disable esm-infra` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua disable esm-infra` with sudo
        Then I will see the following on stdout:
            """
            Updating package lists
            """
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            esm-infra    +yes      +disabled +UA Infra: Extended Security Maintenance
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
            UA Infra: Extended Security Maintenance is enabled by default on entitled
            workloads. It provides access to a private PPA which includes available
            high and critical CVE fixes for Ubuntu LTS packages in the Ubuntu Main
            repository between the end of the standard (free) Ubuntu LTS security
            maintenance and its end of life. You can find out more about the esm
            service at https://ubuntu.com/security/esm.
            """
        When I run `ua help esm-infra --format json` with sudo
        Then I will see the following on stdout:
            """
            {"name": "esm-infra", "entitled": "yes", "status": "enabled", "help": "UA Infra: Extended Security Maintenance is enabled by default on entitled\nworkloads. It provides access to a private PPA which includes available\nhigh and critical CVE fixes for Ubuntu LTS packages in the Ubuntu Main\nrepository between the end of the standard (free) Ubuntu LTS security\nmaintenance and its end of life. You can find out more about the esm\nservice at https://ubuntu.com/security/esm.\n"}
            """
        When I run `ua help invalid-service` with sudo
        Then I will see the following on stderr:
            """
            No help available for 'invalid-service'
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
