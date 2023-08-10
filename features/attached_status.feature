@uses.config.contract_token
Feature: Attached status

    @series.all
    @uses.config.machine_type.lxd-container
    Scenario Outline: Attached status in a ubuntu machine - formatted
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `pro status --format json` as non-root
        Then stdout is a json matching the `ua_status` schema
        When I run `pro status --format yaml` as non-root
        Then stdout is a yaml matching the `ua_status` schema

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
        And I append the following on uaclient config:
        """
        features:
          machine_token_overlay: "/tmp/machine-token-overlay.json"
        """
        And I run `pro status` with sudo
        Then stdout contains substring:
        """
        Valid until: Unknown/Expired
        """

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | jammy   |
           | lunar   |
           | mantic  |

    @series.xenial
    @uses.config.machine_type.lxd-container
    Scenario Outline: Non-root status can see in-progress operations
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        When I run shell command `sudo pro enable cis >/dev/null & pro status` as non-root
        Then stdout matches regexp:
        """
        NOTICES
        Operation in progress: pro enable
        """
        When I run `pro status --wait` as non-root
        When I run `pro disable cis --assume-yes` with sudo
        When I run shell command `sudo pro enable cis & pro status --wait` as non-root
        Then stdout matches regexp:
        """
        One moment, checking your subscription first
        Updating package lists
        Installing CIS Audit packages
        CIS Audit enabled
        Visit https://ubuntu.com/security/cis to learn how to use CIS
        \.+
        SERVICE +ENTITLED +STATUS +DESCRIPTION
        """
        Then stdout does not match regexp:
        """
        NOTICES
        Operation in progress: pro enable
        """
        When I run `pro disable cis --assume-yes` with sudo
        When I run `apt-get install jq -y` with sudo
        When I run shell command `sudo pro enable cis >/dev/null & pro status --format json | jq -r .execution_status` as non-root
        Then I will see the following on stdout:
        """
        active
        """
        Examples: ubuntu release
           | release |
           | xenial  |

    @series.xenial
    @series.bionic
    @uses.config.machine_type.lxd-container
    Scenario Outline: Attached status in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I verify root and non-root `pro status` calls have the same output
        And I run `pro status` as non-root
        Then stdout matches regexp:
        """
        SERVICE         +ENTITLED +STATUS   +DESCRIPTION
        cc-eal          +yes      +disabled +Common Criteria EAL2 Provisioning Packages
        cis             +yes      +disabled +Security compliance and audit tools
        esm-apps        +yes      +enabled  +Expanded Security Maintenance for Applications
        esm-infra       +yes      +enabled  +Expanded Security Maintenance for Infrastructure
        fips            +yes      +disabled +NIST-certified core packages
        fips-updates    +yes      +disabled +NIST-certified core packages with priority security updates
        ros             +yes      +disabled +Security Updates for the Robot Operating System
        ros-updates     +yes      +disabled +All Updates for the Robot Operating System

        For a list of all Ubuntu Pro services, run 'pro status --all'
        Enable services with: pro enable <service>
        """
        When I verify root and non-root `pro status --all` calls have the same output
        And I run `pro status --all` as non-root
        Then stdout matches regexp:
        """
        SERVICE         +ENTITLED +STATUS   +DESCRIPTION
        anbox-cloud     +yes      +n/a      +.*
        cc-eal          +yes      +disabled +Common Criteria EAL2 Provisioning Packages
        cis             +yes      +disabled +Security compliance and audit tools
        esm-apps        +yes      +enabled  +Expanded Security Maintenance for Applications
        esm-infra       +yes      +enabled  +Expanded Security Maintenance for Infrastructure
        fips            +yes      +disabled +NIST-certified core packages
        fips-updates    +yes      +disabled +NIST-certified core packages with priority security updates
        livepatch       +yes      +n/a      +Canonical Livepatch service
        realtime-kernel +yes      +n/a      +Ubuntu kernel with PREEMPT_RT patches integrated
        ros             +yes      +disabled +Security Updates for the Robot Operating System
        ros-updates     +yes      +disabled +All Updates for the Robot Operating System

        Enable services with: pro enable <service>
        """

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |

    @series.focal
    @uses.config.machine_type.lxd-container
    Scenario Outline: Attached status in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I verify root and non-root `pro status` calls have the same output
        And I run `pro status` as non-root
        Then stdout matches regexp:
        """
        SERVICE         +ENTITLED +STATUS   +DESCRIPTION
        esm-apps        +yes      +enabled  +Expanded Security Maintenance for Applications
        esm-infra       +yes      +enabled  +Expanded Security Maintenance for Infrastructure
        fips            +yes      +disabled +NIST-certified core packages
        fips-updates    +yes      +disabled +NIST-certified core packages with priority security updates
        usg             +yes      +disabled +Security compliance and audit tools

        For a list of all Ubuntu Pro services, run 'pro status --all'
        Enable services with: pro enable <service>
        """
        When I verify root and non-root `pro status --all` calls have the same output
        And I run `pro status --all` as non-root
        Then stdout matches regexp:
        """
        SERVICE         +ENTITLED +STATUS   +DESCRIPTION
        anbox-cloud     +yes      +n/a      +.*
        cc-eal          +yes      +n/a      +Common Criteria EAL2 Provisioning Packages
        esm-apps        +yes      +enabled  +Expanded Security Maintenance for Applications
        esm-infra       +yes      +enabled  +Expanded Security Maintenance for Infrastructure
        fips            +yes      +disabled +NIST-certified core packages
        fips-updates    +yes      +disabled +NIST-certified core packages with priority security updates
        livepatch       +yes      +n/a      +Canonical Livepatch service
        realtime-kernel +yes      +n/a      +Ubuntu kernel with PREEMPT_RT patches integrated
        ros             +yes      +n/a      +Security Updates for the Robot Operating System
        ros-updates     +yes      +n/a      +All Updates for the Robot Operating System
        usg             +yes      +disabled +Security compliance and audit tools

        Enable services with: pro enable <service>
        """

        Examples: ubuntu release
           | release |
           | focal   |

    @series.jammy
    @uses.config.machine_type.lxd-container
    Scenario Outline: Attached status in the latest LTS ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I verify root and non-root `pro status` calls have the same output
        And I run `pro status` as non-root
        Then stdout matches regexp:
        """
        SERVICE         +ENTITLED +STATUS   +DESCRIPTION
        anbox-cloud     +yes      +disabled +.*
        esm-apps        +yes      +enabled  +Expanded Security Maintenance for Applications
        esm-infra       +yes      +enabled  +Expanded Security Maintenance for Infrastructure
        usg             +yes      +disabled +Security compliance and audit tools

        For a list of all Ubuntu Pro services, run 'pro status --all'
        Enable services with: pro enable <service>
        """
        When I verify root and non-root `pro status --all` calls have the same output
        And I run `pro status --all` as non-root
        Then stdout matches regexp:
        """
        SERVICE         +ENTITLED +STATUS   +DESCRIPTION
        anbox-cloud     +yes      +disabled +.*
        cc-eal          +yes      +n/a      +Common Criteria EAL2 Provisioning Packages
        esm-apps        +yes      +enabled  +Expanded Security Maintenance for Applications
        esm-infra       +yes      +enabled  +Expanded Security Maintenance for Infrastructure
        fips            +yes      +n/a      +NIST-certified core packages
        fips-updates    +yes      +n/a      +NIST-certified core packages with priority security updates
        livepatch       +yes      +n/a      +Canonical Livepatch service
        realtime-kernel +yes      +n/a      +Ubuntu kernel with PREEMPT_RT patches integrated
        ├ generic       +yes      +n/a      +Generic version of the RT kernel \(default\)
        └ intel-iotg    +yes      +n/a      +RT kernel optimized for Intel IOTG platform
        ros             +yes      +n/a      +Security Updates for the Robot Operating System
        ros-updates     +yes      +n/a      +All Updates for the Robot Operating System
        usg             +yes      +disabled +Security compliance and audit tools

        Enable services with: pro enable <service>
        """

        Examples: ubuntu release
           | release |
           | jammy   |
