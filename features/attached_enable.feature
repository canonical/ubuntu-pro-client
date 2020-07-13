@uses.config.contract_token
Feature: Enable command behaviour when attached to an UA subscription

    @series.all
    Scenario Outline: Attached enable Common Criteria service in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua enable cc-eal` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua enable cc-eal --beta` with sudo
        Then I will see the following on stdout
            """
            One moment, checking your subscription first
            <msg>
            """

        Examples: ubuntu release
           | release | msg                                                            |
           | bionic  | CC EAL2 is not available for Ubuntu 18.04 LTS (Bionic Beaver). |
           | focal   | CC EAL2 is not available for Ubuntu 20.04 LTS (Focal Fossa).   |
           | trusty  | CC EAL2 is not available for Ubuntu 14.04 LTS (Trusty Tahr).   |

    @series.all
    Scenario Outline: Attached enable a disabled beta service and unknown service in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua enable fips foobar` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua enable fips foobar` with sudo
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            """
        And stderr matches regexp:
            """
            Cannot enable 'foobar, fips'
            For a list of services see: sudo ua status
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | trusty  |
           | xenial  |

    @series.all
    Scenario Outline: Attached enable of an unknown service in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua enable foobar` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua enable foobar` with sudo
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            """
        Then stderr matches regexp:
            """
            Cannot enable 'foobar'
            For a list of services see: sudo ua status
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | trusty  |
           | xenial  |

    @series.all
    Scenario Outline: Attached enable of a known service already enabled (UA Infra) in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua enable esm-infra` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua enable esm-infra` with sudo
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            ESM Infra is already enabled.
            See: sudo ua status
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | trusty  |
           | xenial  |

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached enable a disabled, enable and unknown service in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua enable livepatch esm-infra foobar` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua enable livepatch esm-infra foobar` with sudo
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            Cannot install Livepatch on a container
            ESM Infra is already enabled.
            See: sudo ua status
            """
        And stderr matches regexp:
            """
            Cannot enable 'foobar'
            For a list of services see: sudo ua status
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | trusty  |
           | xenial  |

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline:  Attached enable of non-container services in a ubuntu lxd container
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua enable <service> <flag>` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua enable <service> <flag>` with sudo
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            Cannot install <title> on a container
            """

        Examples: Un-supported services in containers
           | release | service      | title        | flag                 |
           | bionic  | livepatch    | Livepatch    |                      |
           | bionic  | fips         | FIPS         | --assume-yes --beta  |
           | bionic  | fips-updates | FIPS Updates | --assume-yes --beta  |
           | focal   | livepatch    | Livepatch    |                      |
           | focal   | fips         | FIPS         | --assume-yes --beta  |
           | focal   | fips-updates | FIPS Updates | --assume-yes --beta  |
           | trusty  | livepatch    | Livepatch    |                      |
           | trusty  | fips         | FIPS         | --assume-yes --beta  |
           | trusty  | fips-updates | FIPS Updates | --assume-yes --beta  |
           | xenial  | livepatch    | Livepatch    |                      |
           | xenial  | fips         | FIPS         | --assume-yes --beta  |
           | xenial  | fips-updates | FIPS Updates | --assume-yes --beta  |

    @series.all
    Scenario Outline:  Attached enable of non-container beta services in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua enable <service> <flag>` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua enable <service> <flag>` with sudo
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            """
        And stderr matches regexp:
            """
            Cannot enable '<service>'
            For a list of services see: sudo ua status
            """

        Examples: beta services in containers
           | release | service      | flag         |
           | bionic  | fips         | --assume-yes |
           | bionic  | fips-updates | --assume-yes |
           | focal   | fips         | --assume-yes |
           | focal   | fips-updates | --assume-yes |
           | trusty  | fips         | --assume-yes |
           | trusty  | fips-updates | --assume-yes |
           | xenial  | fips         | --assume-yes |
           | xenial  | fips-updates | --assume-yes |

    @series.all
    Scenario Outline: Attached enable not entitled service in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua enable <service>` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua enable <service> --beta` with sudo
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            This subscription is not entitled to <title>.
            For more information see: https://ubuntu.com/advantage
            """

        Examples: not entitled services
           | release | service      | title        |
           | bionic  | cis-audit    | CIS Audit    |
           | bionic  | esm-apps     | ESM Apps     |
           | focal   | cis-audit    | CIS Audit    |
           | focal   | esm-apps     | ESM Apps     |
           | trusty  | cis-audit    | CIS Audit    |
           | trusty  | esm-apps     | ESM Apps     |
           | xenial  | cis-audit    | CIS Audit    |
           | xenial  | esm-apps     | ESM Apps     |

    @series.focal
    @uses.config.machine_type.lxd.vm
    Scenario: Attached enable of vm-based services in a focal lxd vm
        Given a `focal` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        When I run `ua enable fips --assume-yes --beta` with sudo
        Then stdout matches regexp:
            """
            FIPS is not available for Ubuntu 20.04 LTS (Focal Fossa).
            """
        When I run `ua enable fips-updates --assume-yes --beta` with sudo
        Then stdout matches regexp:
            """
            FIPS Updates is not available for Ubuntu 20.04 LTS (Focal Fossa).
            """

    @series.xenial
    @uses.config.machine_type.lxd.vm
    Scenario: Attached enable of vm-based services in a bionic lxd vm
        Given a `xenial` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        When I run `ua enable fips --assume-yes --beta` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            Installing FIPS packages
            FIPS enabled
            A reboot is required to complete install
            """

    @series.bionic
    @uses.config.machine_type.lxd.vm
    Scenario: Attached enable of vm-based services in a bionic lxd vm
        Given a `bionic` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        When I run `ua enable fips --assume-yes --beta` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            Installing FIPS packages
            FIPS enabled
            A reboot is required to complete install
            """

    @series.bionic
    @series.xenial
    @uses.config.machine_type.lxd.vm
    Scenario Outline: Attached enable livepatch on a machine with fips active
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `canonical-livepatch status` with sudo
        Then I will see the following on stderr:
            """
            sudo: canonical-livepatch: command not found
            """
        When I attach `contract_token` with sudo
        Then stdout matches regexp:
            """
            Installing canonical-livepatch snap
            Canonical livepatch enabled
            """
        When I run `canonical-livepatch status` with sudo
        Then stdout matches regexp:
            """
            running: true
            """

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
