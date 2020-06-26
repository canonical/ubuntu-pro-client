@uses.config.contract_token
Feature: Enable command behaviour when attached to an UA subscription

    @series.trusty
    Scenario Outline:  Attached enable of non-container services in a trusty lxd container
        Given a `trusty` machine with ubuntu-advantage-tools installed
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
           | service      | title        | flag                 |
           | livepatch    | Livepatch    |                      |
           | fips         | FIPS         | --assume-yes --beta  |
           | fips-updates | FIPS Updates | --assume-yes --beta  |

    @series.trusty
    Scenario Outline:  Attached enable of non-container beta services in a trusty lxd container
        Given a `trusty` machine with ubuntu-advantage-tools installed
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
        And I will see the following on stderr:
            """
            Cannot enable '<service>'
            For a list of services see: sudo ua status
            """

        Examples: beta services in containers
           | service      | flag                |
           | fips         | --assume-yes --beta |
           | fips-updates | --assume-yes --beta |

    @series.trusty
    Scenario: Attached enable Common Criteria service in a trusty lxd container
        Given a `trusty` machine with ubuntu-advantage-tools installed
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
            CC EAL2 is not available for Ubuntu 14.04 LTS (Trusty Tahr).
            """

    @series.trusty
    Scenario Outline: Attached enable not entitled service in a trusty lxd container
        Given a `trusty` machine with ubuntu-advantage-tools installed
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
           | service      | title        |
           | cis-audit    | CIS Audit    |
           | esm-apps     | ESM Apps     |

    @series.trusty
    Scenario: Attached enable of an unknown service in a trusty lxd container
        Given a `trusty` machine with ubuntu-advantage-tools installed
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
        And I will see the following on stderr:
            """
            Cannot enable 'foobar'
            For a list of services see: sudo ua status
            """

    @series.trusty
    Scenario: Attached enable of a known service already enabled (UA Infra) in a trusty lxd container
        Given a `trusty` machine with ubuntu-advantage-tools installed
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

    @series.trusty
    Scenario: Attached enable a disabled, enable and unknown service in a trusty lxd container
        Given a `trusty` lxd container with ubuntu-advantage-tools installed
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
        And I will see the following on stderr:
            """
            Cannot enable 'foobar'
            For a list of services see: sudo ua status
            """

    @series.trusty
    Scenario: Attached enable a disabled beta service and unknown service in a trusty lxd container
        Given a `trusty` lxd container with ubuntu-advantage-tools installed
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

    @series.focal
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached enable of vm-based services in a focal lxd container
        Given a `focal` machine with ubuntu-advantage-tools installed
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
           | service      | title        | flag                 |
           | livepatch    | Livepatch    |                      |
           | fips         | FIPS         | --assume-yes --beta  |
           | fips-updates | FIPS Updates | --assume-yes --beta  |

    @series.focal
    Scenario Outline:  Attached enable of vm-only beta services in a focal machine
        Given a `focal` machine with ubuntu-advantage-tools installed
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
           | service      | flag         |
           | fips         | --assume-yes |
           | fips-updates | --assume-yes |

    @series.focal
    Scenario: Attached enable Common Criteria service in a focal lxd container
        Given a `focal` machine with ubuntu-advantage-tools installed
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
            CC EAL2 is not available for Ubuntu 20.04 LTS (Focal Fossa).
            """

    @series.focal
    Scenario Outline: Attached enable not entitled service in a focal lxd container
        Given a `focal` machine with ubuntu-advantage-tools installed
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
           | service      | title        |
           | cis-audit    | CIS Audit    |
           | esm-apps     | ESM Apps     |

    @series.focal
    Scenario: Attached enable of an unknown service in a focal lxd container
        Given a `focal` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua enable foobar` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua enable foobar` with sudo
        Then stderr matches regexp:
            """
            Cannot enable 'foobar'
            For a list of services see: sudo ua status
            """

    @series.focal
    Scenario: Attached enable of a known service already enabled (UA Infra) in a focal lxd container
        Given a `focal` machine with ubuntu-advantage-tools installed
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

    @series.focal
    Scenario: Attached enable a disabled, enabled and unknown service in a focal lxd container
        Given a `focal` lxd container with ubuntu-advantage-tools installed
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

    @series.focal
    Scenario: Attached enable a disabled beta service and unknown service in a focal lxd container
        Given a `focal` lxd container with ubuntu-advantage-tools installed
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
