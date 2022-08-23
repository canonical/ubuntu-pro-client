@uses.config.contract_token
Feature: Attached status

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached status in a ubuntu machine - formatted
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `pro status --format json` as non-root
        Then stdout is a json matching the `ua_status` schema
        When I run `pro status --format yaml` as non-root
        Then stdout is a yaml matching the `ua_status` schema

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | xenial  |
           | jammy   |
           | kinetic |

    @series.xenial
    @series.bionic
    @uses.config.machine_type.lxd.container
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

        Enable services with: pro enable <service>
        """
        When I verify root and non-root `pro status --all` calls have the same output
        And I run `pro status --all` as non-root
        Then stdout matches regexp:
        """
        SERVICE         +ENTITLED +STATUS   +DESCRIPTION
        cc-eal          +yes      +disabled +Common Criteria EAL2 Provisioning Packages
        cis             +yes      +disabled +Security compliance and audit tools
        esm-apps        +yes      +enabled  +Expanded Security Maintenance for Applications
        esm-infra       +yes      +enabled  +Expanded Security Maintenance for Infrastructure
        fips            +yes      +disabled +NIST-certified core packages
        fips-updates    +yes      +disabled +NIST-certified core packages with priority security updates
        livepatch       +yes      +n/a      +Canonical Livepatch service
        realtime-kernel +yes      +n/a      +Beta-version Ubuntu Kernel with PREEMPT_RT patches
        ros             +yes      +disabled +Security Updates for the Robot Operating System
        ros-updates     +yes      +disabled +All Updates for the Robot Operating System

        Enable services with: pro enable <service>
        """

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |

    @series.focal
    @uses.config.machine_type.lxd.container
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

        Enable services with: pro enable <service>
        """
        When I verify root and non-root `pro status --all` calls have the same output
        And I run `pro status --all` as non-root
        Then stdout matches regexp:
        """
        SERVICE         +ENTITLED +STATUS   +DESCRIPTION
        cc-eal          +yes      +n/a      +Common Criteria EAL2 Provisioning Packages
        esm-apps        +yes      +enabled  +Expanded Security Maintenance for Applications
        esm-infra       +yes      +enabled  +Expanded Security Maintenance for Infrastructure
        fips            +yes      +disabled +NIST-certified core packages
        fips-updates    +yes      +disabled +NIST-certified core packages with priority security updates
        livepatch       +yes      +n/a      +Canonical Livepatch service
        realtime-kernel +yes      +n/a      +Beta-version Ubuntu Kernel with PREEMPT_RT patches
        ros             +yes      +n/a      +Security Updates for the Robot Operating System
        ros-updates     +yes      +n/a      +All Updates for the Robot Operating System
        usg             +yes      +disabled +Security compliance and audit tools

        Enable services with: pro enable <service>
        """

        Examples: ubuntu release
           | release |
           | focal   |

    @series.jammy
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached status in the latest LTS ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I verify root and non-root `pro status` calls have the same output
        And I run `pro status` as non-root
        Then stdout matches regexp:
        """
        SERVICE         +ENTITLED +STATUS   +DESCRIPTION
        esm-apps        +yes      +enabled  +Expanded Security Maintenance for Applications
        esm-infra       +yes      +enabled  +Expanded Security Maintenance for Infrastructure

        Enable services with: pro enable <service>
        """
        When I verify root and non-root `pro status --all` calls have the same output
        And I run `pro status --all` as non-root
        Then stdout matches regexp:
        """
        SERVICE         +ENTITLED +STATUS   +DESCRIPTION
        cc-eal          +yes      +n/a      +Common Criteria EAL2 Provisioning Packages
        esm-apps        +yes      +enabled  +Expanded Security Maintenance for Applications
        esm-infra       +yes      +enabled  +Expanded Security Maintenance for Infrastructure
        fips            +yes      +n/a      +NIST-certified core packages
        fips-updates    +yes      +n/a      +NIST-certified core packages with priority security updates
        livepatch       +yes      +n/a      +Canonical Livepatch service
        realtime-kernel +yes      +n/a      +Beta-version Ubuntu Kernel with PREEMPT_RT patches
        ros             +yes      +n/a      +Security Updates for the Robot Operating System
        ros-updates     +yes      +n/a      +All Updates for the Robot Operating System
        usg             +yes      +n/a      +Security compliance and audit tools

        Enable services with: pro enable <service>
        """

        Examples: ubuntu release
           | release |
           | jammy   |
