@uses.config.contract_token
Feature: Enable command behaviour when attached to an UA subscription

    @series.all
    Scenario Outline: Attached enable Common Criteria service in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua enable cc-eal` `as non-root` exits `1`
        And I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        And I verify that running `ua enable cc-eal --beta` `with sudo` exits `1`
        And I will see the following on stdout
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
        Then I verify that running `ua enable cc-eal foobar` `as non-root` exits `1`
        And I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        And I verify that running `ua enable cc-eal foobar` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            One moment, checking your subscription first
            """
        And stderr matches regexp:
            """
            Cannot enable unknown service 'foobar, cc-eal'.
            Try esm-infra, fips, fips-updates, livepatch
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
        Then I verify that running `ua enable foobar` `as non-root` exits `1`
        And I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        And I verify that running `ua enable foobar` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            One moment, checking your subscription first
            """
        And stderr matches regexp:
            """
            Cannot enable unknown service 'foobar'.
            Try esm-infra, fips, fips-updates, livepatch
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
        Then I verify that running `ua enable esm-infra` `as non-root` exits `1`
        And I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        And I verify that running `ua enable esm-infra` `with sudo` exits `1`
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            ESM Infra is already enabled.
            See: sudo ua status
            """
        When I run `apt-cache policy` with sudo
        Then apt-cache policy for the following url has permission `500`
        """
        <esm-infra-url> <release>-infra-updates/main amd64 Packages
        """
        And I verify that running `apt update` `with sudo` exits `0`
        When I run `apt install -y <infra-pkg>` with sudo
        And I run `apt-cache policy <infra-pkg>` as non-root
        Then stdout matches regexp:
        """
        \s*500 <esm-infra-url> <release>-infra-security/main amd64 Packages
        \s*500 <esm-infra-url> <release>-infra-updates/main amd64 Packages
        """

        Examples: ubuntu release
           | release | infra-pkg | esm-infra-url                       |
           | bionic  | libkrad0  | https://esm.ubuntu.com/infra/ubuntu |
           | focal   | hello     | https://esm.ubuntu.com/infra/ubuntu |
           | trusty  | libgit2-0 | https://esm.ubuntu.com/ubuntu/      |
           | xenial  | libkrad0  | https://esm.ubuntu.com/infra/ubuntu |

    @series.xenial
    @series.bionic
    @series.focal
    Scenario Outline: Attached enable of a know service shows update in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua enable esm-infra` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            One moment, checking your subscription first
            ESM Infra is already enabled.
            See: sudo ua status
            """
        And I verify that running `apt install -y <pkg-version>` `with sudo` exits `0`
        When I run `apt update` with sudo
        Then stdout matches regexp
        """
        \d+ of the updates (is|are) from UA Infra: ESM
        """
        When I run `ua disable esm-infra` with sudo
        And I run `apt update` with sudo
        Then stdout does not match regexp
        """
        \d+ of the updates (is|are) from UA Infra: ESM
        """

        Examples: ubuntu release
           | release | pkg-version            |
           | bionic  | libkrad0=1.16-2build1  |
           | focal   | hello=2.10-2ubuntu2    |
           | xenial  | libkrad0=1.13.2+dfsg-5 |

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached enable a disabled, enable and unknown service in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua enable livepatch esm-infra foobar` `as non-root` exits `1`
        And I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        And I verify that running `ua enable livepatch esm-infra foobar` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            One moment, checking your subscription first
            Cannot install Livepatch on a container
            ESM Infra is already enabled.
            See: sudo ua status
            """
        And stderr matches regexp:
            """
            Cannot enable unknown service 'foobar'.
            Try esm-infra, fips, fips-updates, livepatch
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
        Then I verify that running `ua enable <service> <flag>` `as non-root` exits `1`
        And I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        And I verify that running `ua enable <service> <flag>` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            One moment, checking your subscription first
            Cannot install <title> on a container
            """

        Examples: Un-supported services in containers
           | release | service      | title        | flag         |
           | bionic  | livepatch    | Livepatch    |              |
           | bionic  | fips         | FIPS         | --assume-yes |
           | bionic  | fips-updates | FIPS Updates | --assume-yes |
           | focal   | livepatch    | Livepatch    |              |
           | focal   | fips         | FIPS         | --assume-yes |
           | focal   | fips-updates | FIPS Updates | --assume-yes |
           | trusty  | livepatch    | Livepatch    |              |
           | trusty  | fips         | FIPS         | --assume-yes |
           | trusty  | fips-updates | FIPS Updates | --assume-yes |
           | xenial  | livepatch    | Livepatch    |              |
           | xenial  | fips         | FIPS         | --assume-yes |
           | xenial  | fips-updates | FIPS Updates | --assume-yes |

    @series.all
    Scenario Outline:  Attached enable of non-container beta services in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua enable cc-eal` `as non-root` exits `1`
        And I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        And I verify that running `ua enable cc-eal` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            One moment, checking your subscription first
            """
        And stderr matches regexp:
            """
            Cannot enable unknown service 'cc-eal'.
            Try esm-infra, fips, fips-updates, livepatch
            """
           | release |
           | bionic  |
           | focal   |
           | trusty  |
           | xenial  |

    @series.all
    Scenario Outline: Attached enable not entitled service in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua enable <service>` `as non-root` exits `1`
        And I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        And I verify that running `ua enable <service> --beta` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            One moment, checking your subscription first
            This subscription is not entitled to <title>.
            For more information see: https://ubuntu.com/advantage
            """

        Examples: not entitled services
           | release | service      | title        |
           | bionic  | cis          | CIS Audit    |
           | bionic  | esm-apps     | ESM Apps     |
           | focal   | cis          | CIS Audit    |
           | focal   | esm-apps     | ESM Apps     |
           | trusty  | cis          | CIS Audit    |
           | trusty  | esm-apps     | ESM Apps     |
           | xenial  | cis          | CIS Audit    |
           | xenial  | esm-apps     | ESM Apps     |

    @series.focal
    @uses.config.machine_type.lxd.vm
    Scenario: Attached enable of vm-based services in a focal lxd vm
        Given a `focal` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua enable fips --assume-yes` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            One moment, checking your subscription first
            FIPS is not available for Ubuntu 20.04 LTS (Focal Fossa).
            """
        And I verify that running `ua enable fips-updates --assume-yes` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            One moment, checking your subscription first
            FIPS Updates is not available for Ubuntu 20.04 LTS (Focal Fossa).
            """

    @series.bionic
    @series.xenial
    @uses.config.machine_type.lxd.vm
    Scenario Outline: Attached enable of vm-based services in a bionic lxd vm
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua status` with sudo
        Then stdout matches regexp:
        """
        esm-infra    +yes      +enabled  +UA Infra: Extended Security Maintenance \(ESM\)
        fips         +yes      +n/a      +NIST-certified FIPS modules
        fips-updates +yes      +n/a      +Uncertified security updates to FIPS modules
        livepatch    +yes      +enabled  +Canonical Livepatch service
        """
        When I run `ua disable livepatch` with sudo
        Then I verify that running `canonical-livepatch status` `with sudo` exits `1`
        And stdout matches regexp:
        """
        Machine is not enabled. Please run 'sudo canonical-livepatch enable' with the
        token obtained from https://ubuntu.com/livepatch.
        """
        When I run `ua status` with sudo
        Then stdout matches regexp:
        """
        esm-infra    +yes      +enabled  +UA Infra: Extended Security Maintenance \(ESM\)
        fips         +yes      +disabled +NIST-certified FIPS modules
        fips-updates +yes      +disabled +Uncertified security updates to FIPS modules
        livepatch    +yes      +disabled +Canonical Livepatch service
        """

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |

    @series.bionic
    @series.xenial
    @uses.config.machine_type.lxd.vm
    Scenario Outline: Attached enable livepatch on a machine with fips active
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I verify that running `canonical-livepatch status` `with sudo` exits `1`
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
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            livepatch     yes                enabled
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

    @series.bionic
    @uses.config.machine_type.lxd.vm
    Scenario: Attached enable fips on a machine with livepatch active
        Given a `bionic` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            ESM Infra enabled
            Installing canonical-livepatch snap
            Canonical livepatch enabled
            """
        When I run `ua disable livepatch` with sudo
        And I run `ua enable fips --assume-yes` with sudo
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            Updating package lists
            Installing FIPS packages
            FIPS enabled
            A reboot is required to complete install
            """
        When I append the following on uaclient config:
            """
            features:
              block_disable_on_enable: true
            """
        Then I verify that running `ua enable livepatch` `with sudo` exits `1`
        And I will see the following on stdout
            """
            One moment, checking your subscription first
            Cannot enable Livepatch when FIPS is enabled
            """

    @series.bionic
    @uses.config.machine_type.lxd.vm
    Scenario: Attached enable livepatch on a machine with fips active
        Given a `bionic` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            ESM Infra enabled
            Installing canonical-livepatch snap
            Canonical livepatch enabled
            """
        When I append the following on uaclient config:
        """
        features:
          block_disable_on_enable: true
        """
        Then I verify that running `ua enable fips --assume-yes` `with sudo` exits `1`
        And I will see the following on stdout
            """
            One moment, checking your subscription first
            Cannot enable FIPS when Livepatch is enabled
            """

    @series.xenial
    @series.bionic
    @uses.config.machine_type.lxd.vm
    Scenario Outline: Attached enable fips on a machine with livepatch active
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            ESM Infra enabled
            """
        And stdout matches regexp:
            """
            Installing canonical-livepatch snap
            Canonical livepatch enabled
            """
        When I run `ua enable fips --assume-yes` with sudo
        Then I will see the following on stdout
            """
            One moment, checking your subscription first
            Updating package lists
            Installing FIPS packages
            FIPS enabled
            A reboot is required to complete install
            """
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            fips +yes +enabled
            """
        And stdout matches regexp:
            """
            livepatch +yes +n/a
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | xenial  |

    @series.xenial
    @series.bionic
    @uses.config.machine_type.lxd.vm
    Scenario Outline: Attached enable fips on a machine with fips-updates active
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            ESM Infra enabled
            Installing canonical-livepatch snap
            Canonical livepatch enabled
            """
        When I run `ua disable livepatch` with sudo
        And I run `ua enable fips-updates --assume-yes` with sudo
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            Updating package lists
            Installing FIPS Updates packages
            FIPS Updates enabled
            A reboot is required to complete install
            """
        When I verify that running `ua enable fips --assume-yes` `with sudo` exits `1`
        Then I will see the following on stdout
            """
            One moment, checking your subscription first
            Cannot enable FIPS when FIPS Updates is enabled
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | xenial  |
