@uses.config.contract_token
Feature: Command behaviour when attached to an UA subscription

    @series.trusty
    Scenario: Attached refresh in a trusty machine
        Given a `trusty` machine with ubuntu-advantage-tools installed
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

    @series.trusty
    Scenario: Attached disable of an already disabled service in a trusty machine
        Given a `trusty` machine with ubuntu-advantage-tools installed
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

    @series.trusty
    Scenario: Attached disable of an unknown service in a trusty machine
        Given a `trusty` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua disable foobar` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua disable foobar` with sudo
        Then I will see the following on stderr:
            """
            Cannot disable 'foobar'
            For a list of services see: sudo ua status
            """

    @series.trusty
    Scenario: Attached disable of different services in a trusty machine
        Given a `trusty` machine with ubuntu-advantage-tools installed
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
            Cannot disable 'foobar'
            For a list of services see: sudo ua status
            """
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            esm-infra    +yes      +disabled +UA Infra: Extended Security Maintenance
            """
        When I run `apt-cache policy` with sudo
        Then stdout matches regexp:
            """
            -32768 https://esm.ubuntu.com/ubuntu/ trusty-infra-updates/main amd64 Packages
            """
        And stdout matches regexp:
            """
            -32768 https://esm.ubuntu.com/ubuntu/ trusty-infra-security/main amd64 Packages
            """

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
        When I run `apt-cache policy` with sudo
        Then stdout matches regexp:
            """
            -32768 https://esm.ubuntu.com/ubuntu/ trusty-infra-updates/main amd64 Packages
            """
        And stdout matches regexp:
            """
            -32768 https://esm.ubuntu.com/ubuntu/ trusty-infra-security/main amd64 Packages
            """

    @series.trusty
    Scenario: Attached detach in a trusty machine
        Given a `trusty` machine with ubuntu-advantage-tools installed
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
           cc-eal        +no         +Common Criteria EAL2 Provisioning Packages
           esm-apps      +no         +UA Apps: Extended Security Maintenance
           esm-infra     +yes        +UA Infra: Extended Security Maintenance
           fips          +no         +NIST-certified FIPS modules
           fips-updates  +no         +Uncertified security updates to FIPS modules
           livepatch     +yes        +Canonical Livepatch service
           """
       And stdout matches regexp:
          """
          This machine is not attached to a UA subscription.
          """

    @series.trusty
    Scenario: Attached auto-attach in a trusty machine
        Given a `trusty` machine with ubuntu-advantage-tools installed
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

    @series.trusty
    Scenario: Attached show version in a trusty machine
        Given a `trusty` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua version` as non-root
        Then I will see the uaclient version on stdout
        When I run `ua version` with sudo
        Then I will see the uaclient version on stdout
        When I run `ua --version` as non-root
        Then I will see the uaclient version on stdout
        When I run `ua --version` with sudo
        Then I will see the uaclient version on stdout

    @series.trusty
    Scenario: Unattached status in a trusty machine with machine token overlay
        Given a `trusty` machine with ubuntu-advantage-tools installed
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
        """
        And I attach `contract_token` with sudo
        And I run `ua status --all` with sudo
        Then stdout matches regexp:
            """
            SERVICE       ENTITLED  STATUS    DESCRIPTION
            cc-eal        no
            """
        When I run `ua --version` as non-root
        Then I will see the uaclient version on stdout with overlay info
        When I run `ua version` as non-root
        Then I will see the uaclient version on stdout with overlay info

   @series.focal
   Scenario: Attached refresh in a focal machine
        Given a `focal` machine with ubuntu-advantage-tools installed
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

    @series.focal
    Scenario: Attached disable of an already disabled service in a focal machine
        Given a `focal` machine with ubuntu-advantage-tools installed
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

    @series.focal
    Scenario: Attached disable of an already disabled, enabled and not found services
        Given a `focal` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua disable livepatch esm-infra foobar` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua disable livepatch esm-infra foobar` with sudo
        Then I will see the following on stdout:
            """
            Livepatch is not currently enabled
            See: sudo ua status
            Updating package lists
            """
        And stderr matches regexp:
            """
            Cannot disable 'foobar'
            For a list of services see: sudo ua status
            """
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            esm-infra    +yes      +disabled +UA Infra: Extended Security Maintenance
            """

    @series.focal
    Scenario: Attached disable of an unknown service in a focal machine
        Given a `focal` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua disable foobar` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua disable foobar` with sudo
        Then stderr matches regexp:

            """
            Cannot disable 'foobar'
            For a list of services see: sudo ua status
            """

    @series.focal
    Scenario: Attached disable of an already enabled service in a focal machine
        Given a `focal` machine with ubuntu-advantage-tools installed
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

    @series.focal
    Scenario: Attached detach in a focal machine
        Given a `focal` machine with ubuntu-advantage-tools installed
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
           cc-eal        +no         +Common Criteria EAL2 Provisioning Packages
           esm-apps      +yes        +UA Apps: Extended Security Maintenance
           esm-infra     +yes        +UA Infra: Extended Security Maintenance
           fips          +no         +NIST-certified FIPS modules
           fips-updates  +no         +Uncertified security updates to FIPS modules
           livepatch     +yes        +Canonical Livepatch service
           """
       And stdout matches regexp:
          """
          This machine is not attached to a UA subscription.
          """

    @series.focal
    Scenario: Attached auto-attach in a focal machine
        Given a `focal` machine with ubuntu-advantage-tools installed
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

    @series.focal
    Scenario: Attached show version in a focal machine
        Given a `focal` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua version` as non-root
        Then I will see the uaclient version on stdout
        When I run `ua version` with sudo
        Then I will see the uaclient version on stdout
        When I run `ua --version` as non-root
        Then I will see the uaclient version on stdout
        When I run `ua --version` with sudo
        Then I will see the uaclient version on stdout

    @series.focal
    Scenario: Unattached status in a focal machine with machine token overlay
        Given a `focal` machine with ubuntu-advantage-tools installed
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
        """
        And I attach `contract_token` with sudo
        And I run `ua status --all` with sudo
        Then stdout matches regexp:
            """
            SERVICE       ENTITLED  STATUS    DESCRIPTION
            cc-eal        no
            """
        When I run `ua --version` as non-root
        Then I will see the uaclient version on stdout with overlay info
        When I run `ua version` as non-root
        Then I will see the uaclient version on stdout with overlay info
