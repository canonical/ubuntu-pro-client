@uses.config.contract_token
Feature: Enable command behaviour when attached to an UA subscription

    @series.trusty
    Scenario Outline:  Attached enable of non-container services in a trusty lxd container
        Given a `trusty` lxd container with ubuntu-advantage-tools installed
        When I attach contract_token with sudo
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
           | service      | title        | flag          |
           | livepatch    | Livepatch    |               |
           | fips         | FIPS         | --assume-yes  |
           | fips-updates | FIPS Updates | --assume-yes  |

    @series.trusty
    Scenario: Attached enable Common Criteria service in a trusty lxd container
        Given a `trusty` lxd container with ubuntu-advantage-tools installed
        When I attach contract_token with sudo
        And I run `ua enable cc-eal` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua enable cc-eal` with sudo
        Then I will see the following on stdout
            """
            One moment, checking your subscription first
            CC EAL2 is not available for Ubuntu 14.04 LTS (Trusty Tahr).
            """

    @series.trusty
    Scenario: Attached enable CIS Audit service in a trusty lxd container
        Given a `trusty` lxd container with ubuntu-advantage-tools installed
        When I attach contract_token with sudo
        And I run `ua enable cis-audit` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua enable cis-audit` with sudo
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            This subscription is not entitled to CIS Audit.
            For more information see: https://ubuntu.com/advantage
            """

    @series.trusty
    Scenario: Attached enable UA Apps service in a trusty lxd container
        Given a `trusty` lxd container with ubuntu-advantage-tools installed
        When I attach contract_token with sudo
        And I run `ua enable esm-apps` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua enable esm-apps` with sudo
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            This subscription is not entitled to ESM Apps.
            For more information see: https://ubuntu.com/advantage
            """

    @series.trusty
    Scenario: Attached enable of an unknown service in a trusty lxd container
        Given a `trusty` lxd container with ubuntu-advantage-tools installed
        When I attach contract_token with sudo
        And I run `ua enable foobar` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua enable foobar` with sudo
        Then I will see the following on stderr:
            """
            Cannot enable 'foobar'
            For a list of services see: sudo ua status
            """

    @series.trusty
    Scenario: Attached enable of a known service already enabled (UA Infra) in a trusty lxd container
        Given a `trusty` lxd container with ubuntu-advantage-tools installed
        When I attach contract_token with sudo
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
    Scenario Outline: Attached enable of non-container services in a focal lxd container
        Given a `focal` lxd container with ubuntu-advantage-tools installed
        When I attach contract_token with sudo
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
           | service      | title        | flag          |
           | livepatch    | Livepatch    |               |
           | fips         | FIPS         | --assume-yes  |
           | fips-updates | FIPS Updates | --assume-yes  |



    @series.focal
    Scenario: Attached enable Common Criteria service in a focal lxd container
        Given a `focal` lxd container with ubuntu-advantage-tools installed
        When I attach contract_token with sudo
        And I run `ua enable cc-eal` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua enable cc-eal` with sudo
        Then I will see the following on stdout
            """
            One moment, checking your subscription first
            CC EAL2 is not available for Ubuntu 20.04 LTS (Focal Fossa).
            """

    @series.focal
    Scenario: Attached enable CIS Audit service in a focal lxd container
        Given a `focal` lxd container with ubuntu-advantage-tools installed
        When I attach contract_token with sudo
        And I run `ua enable cis-audit` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua enable cis-audit` with sudo
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            This subscription is not entitled to CIS Audit.
            For more information see: https://ubuntu.com/advantage
            """

    @series.focal
    Scenario: Attached enable UA Apps service in a focal lxd container
        Given a `focal` lxd container with ubuntu-advantage-tools installed
        When I attach contract_token with sudo
        And I run `ua enable esm-apps` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua enable esm-apps` with sudo
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            This subscription is not entitled to ESM Apps.
            For more information see: https://ubuntu.com/advantage
            """


    @series.focal
    Scenario: Attached enable of an unknown service in a focal lxd container
        Given a `focal` lxd container with ubuntu-advantage-tools installed
        When I attach contract_token with sudo
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
        Given a `focal` lxd container with ubuntu-advantage-tools installed
        When I attach contract_token with sudo
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

