Feature: Unattached status

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Unattached status in a ubuntu machine - formatted
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `pro status --format json` as non-root
        Then stdout is a json matching the `ua_status` schema
        When I run `pro status --format yaml` as non-root
        Then stdout is a yaml matching the `ua_status` schema
        When I run `sed -i 's/contracts.can/invalidurl.notcan/' /etc/ubuntu-advantage/uaclient.conf` with sudo
        And I verify that running `pro status --format json` `as non-root` exits `1`
        Then stdout is a json matching the `ua_status` schema
        And I will see the following on stdout:
            """
            {"environment_vars": [], "errors": [{"message": "Failed to connect to authentication server\nCheck your Internet connection and try again.", "message_code": "connectivity-error", "service": null, "type": "system"}], "result": "failure", "services": [], "warnings": []}
            """
        And I verify that running `pro status --format yaml` `as non-root` exits `1`
        Then stdout is a yaml matching the `ua_status` schema
        And I will see the following on stdout:
            """
            environment_vars: []
            errors:
            - message: 'Failed to connect to authentication server

                Check your Internet connection and try again.'
              message_code: connectivity-error
              service: null
              type: system
            result: failure
            services: []
            warnings: []
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | xenial  |
           | jammy   |
           | kinetic |
           | lunar   |

    @series.xenial
    @series.bionic
    @uses.config.machine_type.lxd.container
    Scenario Outline: Unattached status in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I verify root and non-root `pro status` calls have the same output
        And I run `pro status` as non-root
        Then stdout matches regexp:
        """
        SERVICE         +AVAILABLE +DESCRIPTION
        cc-eal          +yes       +Common Criteria EAL2 Provisioning Packages
        cis             +yes       +Security compliance and audit tools
        esm-apps        +yes       +Expanded Security Maintenance for Applications
        esm-infra       +yes       +Expanded Security Maintenance for Infrastructure
        fips            +yes       +NIST-certified core packages
        fips-updates    +yes       +NIST-certified core packages with priority security updates
        livepatch       +yes       +Canonical Livepatch service
        ros             +yes       +Security Updates for the Robot Operating System
        ros-updates     +yes       +All Updates for the Robot Operating System

        This machine is not attached to an Ubuntu Pro subscription.
        See https://ubuntu.com/pro
        """
        When I verify root and non-root `pro status --all` calls have the same output
        And I run `pro status --all` as non-root
        Then stdout matches regexp:
        """
        SERVICE         +AVAILABLE +DESCRIPTION
        cc-eal          +yes       +Common Criteria EAL2 Provisioning Packages
        cis             +yes       +Security compliance and audit tools
        esm-apps        +yes       +Expanded Security Maintenance for Applications
        esm-infra       +yes       +Expanded Security Maintenance for Infrastructure
        fips            +yes       +NIST-certified core packages
        fips-updates    +yes       +NIST-certified core packages with priority security updates
        livepatch       +yes       +Canonical Livepatch service
        realtime-kernel +no        +Ubuntu kernel with PREEMPT_RT patches integrated
        ros             +yes       +Security Updates for the Robot Operating System
        ros-updates     +yes       +All Updates for the Robot Operating System

        This machine is not attached to an Ubuntu Pro subscription.
        See https://ubuntu.com/pro
        """
        When I append the following on uaclient config:
        """
        features:
            allow_beta: true
        """
        And I verify root and non-root `pro status` calls have the same output
        And I run `pro status` as non-root
        Then stdout matches regexp:
        """
        SERVICE         +AVAILABLE +DESCRIPTION
        cc-eal          +yes       +Common Criteria EAL2 Provisioning Packages
        cis             +yes       +Security compliance and audit tools
        esm-apps        +yes       +Expanded Security Maintenance for Applications
        esm-infra       +yes       +Expanded Security Maintenance for Infrastructure
        fips            +yes       +NIST-certified core packages
        fips-updates    +yes       +NIST-certified core packages with priority security updates
        livepatch       +yes       +Canonical Livepatch service
        ros             +yes       +Security Updates for the Robot Operating System
        ros-updates     +yes       +All Updates for the Robot Operating System

        FEATURES
        allow_beta: True

        This machine is not attached to an Ubuntu Pro subscription.
        See https://ubuntu.com/pro
        """ 

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |

    @series.focal
    @uses.config.machine_type.lxd.container
    Scenario Outline: Unattached status in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I verify root and non-root `pro status` calls have the same output
        When I run `pro status` as non-root
        Then stdout matches regexp:
        """
        SERVICE         +AVAILABLE +DESCRIPTION
        esm-apps        +yes       +Expanded Security Maintenance for Applications
        esm-infra       +yes       +Expanded Security Maintenance for Infrastructure
        fips            +yes       +NIST-certified core packages
        fips-updates    +yes       +NIST-certified core packages with priority security updates
        livepatch       +yes       +Canonical Livepatch service
        usg             +yes       +Security compliance and audit tools

        This machine is not attached to an Ubuntu Pro subscription.
        See https://ubuntu.com/pro
        """
        When I verify root and non-root `pro status --all` calls have the same output
        And I run `pro status --all` as non-root
        Then stdout matches regexp:
        """
        SERVICE         +AVAILABLE +DESCRIPTION
        cc-eal          +no        +Common Criteria EAL2 Provisioning Packages
        esm-apps        +yes       +Expanded Security Maintenance for Applications
        esm-infra       +yes       +Expanded Security Maintenance for Infrastructure
        fips            +yes       +NIST-certified core packages
        fips-updates    +yes       +NIST-certified core packages with priority security updates
        livepatch       +yes       +Canonical Livepatch service
        realtime-kernel +no        +Ubuntu kernel with PREEMPT_RT patches integrated
        ros             +no        +Security Updates for the Robot Operating System
        ros-updates     +no        +All Updates for the Robot Operating System
        usg             +yes       +Security compliance and audit tools

        This machine is not attached to an Ubuntu Pro subscription.
        See https://ubuntu.com/pro
        """
        When I append the following on uaclient config:
        """
        features:
            allow_beta: true
        """
        When I verify root and non-root `pro status` calls have the same output
        And I run `pro status` as non-root
        Then stdout matches regexp:
        """
        SERVICE         +AVAILABLE +DESCRIPTION
        esm-apps        +yes       +Expanded Security Maintenance for Applications
        esm-infra       +yes       +Expanded Security Maintenance for Infrastructure
        fips            +yes       +NIST-certified core packages
        fips-updates    +yes       +NIST-certified core packages with priority security updates
        livepatch       +yes       +Canonical Livepatch service
        usg             +yes       +Security compliance and audit tools

        FEATURES
        allow_beta: True

        This machine is not attached to an Ubuntu Pro subscription.
        See https://ubuntu.com/pro
        """ 

        Examples: ubuntu release
           | release |
           | focal   |

    @series.jammy
    @uses.config.machine_type.lxd.container
    Scenario Outline: Unattached status in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I verify root and non-root `pro status` calls have the same output
        And I run `pro status` as non-root
        Then stdout matches regexp:
        """
        SERVICE         +AVAILABLE +DESCRIPTION
        esm-apps        +yes       +Expanded Security Maintenance for Applications
        esm-infra       +yes       +Expanded Security Maintenance for Infrastructure
        livepatch       +yes       +Canonical Livepatch service
        realtime-kernel +yes       +Ubuntu kernel with PREEMPT_RT patches integrated

        This machine is not attached to an Ubuntu Pro subscription.
        See https://ubuntu.com/pro
        """
        When I verify root and non-root `pro status --all` calls have the same output
        And I run `pro status --all` as non-root
        Then stdout matches regexp:
        """
        SERVICE         +AVAILABLE +DESCRIPTION
        cc-eal          +no        +Common Criteria EAL2 Provisioning Packages
        esm-apps        +yes       +Expanded Security Maintenance for Applications
        esm-infra       +yes       +Expanded Security Maintenance for Infrastructure
        fips            +no        +NIST-certified core packages
        fips-updates    +no        +NIST-certified core packages with priority security updates
        livepatch       +yes       +Canonical Livepatch service
        realtime-kernel +yes       +Ubuntu kernel with PREEMPT_RT patches integrated
        ros             +no        +Security Updates for the Robot Operating System
        ros-updates     +no        +All Updates for the Robot Operating System
        usg             +no        +Security compliance and audit tools

        This machine is not attached to an Ubuntu Pro subscription.
        See https://ubuntu.com/pro
        """
        When I append the following on uaclient config:
        """
        features:
            allow_beta: true
        """
        When I verify root and non-root `pro status` calls have the same output
        And I run `pro status` as non-root
        Then stdout matches regexp:
        """
        SERVICE         +AVAILABLE +DESCRIPTION
        esm-apps        +yes       +Expanded Security Maintenance for Applications
        esm-infra       +yes       +Expanded Security Maintenance for Infrastructure
        livepatch       +yes       +Canonical Livepatch service
        realtime-kernel +yes       +Ubuntu kernel with PREEMPT_RT patches integrated

        FEATURES
        allow_beta: True

        This machine is not attached to an Ubuntu Pro subscription.
        See https://ubuntu.com/pro
        """ 

        Examples: ubuntu release
           | release |
           | jammy   |

    @series.xenial
    @series.bionic
    @uses.config.machine_type.lxd.container
    @uses.config.contract_token
    Scenario Outline: Simulate status in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I do a preflight check for `contract_token` without the all flag
        Then stdout matches regexp:
        """
        SERVICE         +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
        cc-eal          +yes       +yes       +no           +Common Criteria EAL2 Provisioning Packages
        cis             +yes       +yes       +no           +Security compliance and audit tools
        esm-apps        +yes       +yes       +yes          +Expanded Security Maintenance for Applications
        esm-infra       +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
        fips            +yes       +yes       +no           +NIST-certified core packages
        fips-updates    +yes       +yes       +no           +NIST-certified core packages with priority security updates
        livepatch       +yes       +yes       +yes          +Canonical Livepatch service
        """
        When I do a preflight check for `contract_token` with the all flag
        Then stdout matches regexp:
        """
        SERVICE         +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
        cc-eal          +yes       +yes       +no           +Common Criteria EAL2 Provisioning Packages
        cis             +yes       +yes       +no           +Security compliance and audit tools
        esm-apps        +yes       +yes       +yes          +Expanded Security Maintenance for Applications
        esm-infra       +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
        fips            +yes       +yes       +no           +NIST-certified core packages
        fips-updates    +yes       +yes       +no           +NIST-certified core packages with priority security updates
        livepatch       +yes       +yes       +yes          +Canonical Livepatch service
        realtime-kernel +no        +yes       +no           +Ubuntu kernel with PREEMPT_RT patches integrated
        ros             +yes       +yes       +no           +Security Updates for the Robot Operating System
        ros-updates     +yes       +yes       +no           +All Updates for the Robot Operating System
        """
        When I do a preflight check for `contract_token` formatted as json
        Then stdout is a json matching the `ua_status` schema
        When I do a preflight check for `contract_token` formatted as yaml
        Then stdout is a yaml matching the `ua_status` schema
        When I verify that a preflight check for `invalid_token` formatted as json exits 1
        Then stdout is a json matching the `ua_status` schema
        And I will see the following on stdout:
            """
            {"environment_vars": [], "errors": [{"message": "Invalid token. See https://ubuntu.com/pro", "message_code": "attach-invalid-token", "service": null, "type": "system"}], "result": "failure", "services": [], "warnings": []}
            """
        When I verify that a preflight check for `invalid_token` formatted as yaml exits 1
        Then stdout is a yaml matching the `ua_status` schema
        And I will see the following on stdout:
            """
            environment_vars: []
            errors:
            - message: Invalid token. See https://ubuntu.com/pro
              message_code: attach-invalid-token
              service: null
              type: system
            result: failure
            services: []
            warnings: []
            """
        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |

    @series.focal
    @uses.config.machine_type.lxd.container
    @uses.config.contract_token
    Scenario Outline: Simulate status in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I do a preflight check for `contract_token` without the all flag
        Then stdout matches regexp:
        """
        SERVICE         +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
        esm-apps        +yes       +yes       +yes          +Expanded Security Maintenance for Applications
        esm-infra       +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
        fips            +yes       +yes       +no           +NIST-certified core packages
        fips-updates    +yes       +yes       +no           +NIST-certified core packages with priority security updates
        livepatch       +yes       +yes       +yes          +Canonical Livepatch service
        usg             +yes       +yes       +no           +Security compliance and audit tools
        """
        When I do a preflight check for `contract_token` with the all flag
        Then stdout matches regexp:
        """
        SERVICE         +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
        cc-eal          +no        +yes       +no           +Common Criteria EAL2 Provisioning Packages
        esm-apps        +yes       +yes       +yes          +Expanded Security Maintenance for Applications
        esm-infra       +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
        fips            +yes       +yes       +no           +NIST-certified core packages
        fips-updates    +yes       +yes       +no           +NIST-certified core packages with priority security updates
        livepatch       +yes       +yes       +yes          +Canonical Livepatch service
        realtime-kernel +no        +yes       +no           +Ubuntu kernel with PREEMPT_RT patches integrated
        ros             +no        +yes       +no           +Security Updates for the Robot Operating System
        ros-updates     +no        +yes       +no           +All Updates for the Robot Operating System
        usg             +yes       +yes       +no           +Security compliance and audit tools
        """
        When I do a preflight check for `contract_token` formatted as json
        Then stdout is a json matching the `ua_status` schema
        When I do a preflight check for `contract_token` formatted as yaml
        Then stdout is a yaml matching the `ua_status` schema
        When I verify that a preflight check for `invalid_token` formatted as json exits 1
        Then stdout is a json matching the `ua_status` schema
        And I will see the following on stdout:
        """
        {"environment_vars": [], "errors": [{"message": "Invalid token. See https://ubuntu.com/pro", "message_code": "attach-invalid-token", "service": null, "type": "system"}], "result": "failure", "services": [], "warnings": []}
        """
        When I verify that a preflight check for `invalid_token` formatted as yaml exits 1
        Then stdout is a yaml matching the `ua_status` schema
        And I will see the following on stdout:
        """
        environment_vars: []
        errors:
        - message: Invalid token. See https://ubuntu.com/pro
          message_code: attach-invalid-token
          service: null
          type: system
        result: failure
        services: []
        warnings: []
        """

        Examples: ubuntu release
           | release |
           | focal   |

    @series.jammy
    @uses.config.machine_type.lxd.container
    @uses.config.contract_token
    Scenario Outline: Simulate status in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I do a preflight check for `contract_token` without the all flag
        Then stdout matches regexp:
        """
        SERVICE         +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
        esm-apps        +yes       +yes       +yes          +Expanded Security Maintenance for Applications
        esm-infra       +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
        livepatch       +yes       +yes       +yes          +Canonical Livepatch service
        """
        When I do a preflight check for `contract_token` with the all flag
        Then stdout matches regexp:
        """
        SERVICE         +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
        cc-eal          +no        +yes       +no           +Common Criteria EAL2 Provisioning Packages
        esm-apps        +yes       +yes       +yes          +Expanded Security Maintenance for Applications
        esm-infra       +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
        fips            +no        +yes       +no           +NIST-certified core packages
        fips-updates    +no        +yes       +no           +NIST-certified core packages with priority security updates
        livepatch       +yes       +yes       +yes          +Canonical Livepatch service
        realtime-kernel +yes       +yes       +no           +Ubuntu kernel with PREEMPT_RT patches integrated
        ros             +no        +yes       +no           +Security Updates for the Robot Operating System
        ros-updates     +no        +yes       +no           +All Updates for the Robot Operating System
        usg             +no        +yes       +no           +Security compliance and audit tools
        """
        When I do a preflight check for `contract_token` formatted as json
        Then stdout is a json matching the `ua_status` schema
        When I do a preflight check for `contract_token` formatted as yaml
        Then stdout is a yaml matching the `ua_status` schema
        When I verify that a preflight check for `invalid_token` formatted as json exits 1
        Then stdout is a json matching the `ua_status` schema
        And I will see the following on stdout:
        """
        {"environment_vars": [], "errors": [{"message": "Invalid token. See https://ubuntu.com/pro", "message_code": "attach-invalid-token", "service": null, "type": "system"}], "result": "failure", "services": [], "warnings": []}
        """
        When I verify that a preflight check for `invalid_token` formatted as yaml exits 1
        Then stdout is a yaml matching the `ua_status` schema
        And I will see the following on stdout:
        """
        environment_vars: []
        errors:
        - message: Invalid token. See https://ubuntu.com/pro
          message_code: attach-invalid-token
          service: null
          type: system
        result: failure
        services: []
        warnings: []
        """

        Examples: ubuntu release
           | release |
           | jammy   |


    @series.xenial
    @series.bionic
    @uses.config.machine_type.lxd.container
    @uses.config.contract_token_staging_expired
    Scenario Outline: Simulate status with expired token in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `sed -i 's/contracts.can/contracts.staging.can/' /etc/ubuntu-advantage/uaclient.conf` with sudo
        And I verify that a preflight check for `contract_token_staging_expired` formatted as json exits 1
        Then stdout is a json matching the `ua_status` schema
        And stdout matches regexp:
            """
            \"result\": \"failure\"
            """
        And stdout matches regexp:
            """
            \"message\": \"Contract .* expired on .*\"
            """
        When I verify that a preflight check for `contract_token_staging_expired` formatted as yaml exits 1
        Then stdout is a yaml matching the `ua_status` schema
        Then stdout matches regexp:
            """
            errors:
            - message: Contract .* expired on .*
            """
        When I verify that a preflight check for `contract_token_staging_expired` without the all flag exits 1
        Then stdout matches regexp:
            """
            This token is not valid.
            Contract \".*\" expired on .*

            SERVICE         +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
            cc-eal          +yes       +yes       +no           +Common Criteria EAL2 Provisioning Packages
            cis             +yes       +yes       +no           +Security compliance and audit tools
            esm-apps        +yes       +no        +no           +Expanded Security Maintenance for Applications
            esm-infra       +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
            fips            +yes       +yes       +no           +NIST-certified core packages
            fips-updates    +yes       +yes       +no           +NIST-certified core packages with priority security updates
            livepatch       +yes       +yes       +yes          +Canonical Livepatch service
            ros             +yes       +no        +no           +Security Updates for the Robot Operating System
            ros-updates     +yes       +no        +no           +All Updates for the Robot Operating System
            """

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |

    @series.focal
    @uses.config.machine_type.lxd.container
    @uses.config.contract_token_staging_expired
    Scenario Outline: Simulate status with expired token in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `sed -i 's/contracts.can/contracts.staging.can/' /etc/ubuntu-advantage/uaclient.conf` with sudo
        And I verify that a preflight check for `contract_token_staging_expired` formatted as json exits 1
        Then stdout is a json matching the `ua_status` schema
        And stdout matches regexp:
        """
        \"result\": \"failure\"
        """
        And stdout matches regexp:
        """
        \"message\": \"Contract .* expired on .*\"
        """
        When I verify that a preflight check for `contract_token_staging_expired` formatted as yaml exits 1
        Then stdout is a yaml matching the `ua_status` schema
        Then stdout matches regexp:
        """
        errors:
        - message: Contract .* expired on .*
        """
        When I verify that a preflight check for `contract_token_staging_expired` without the all flag exits 1
        Then stdout matches regexp:
        """
        This token is not valid.
        Contract \".*\" expired on .*

        SERVICE         +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
        esm-apps        +yes       +no        +no           +Expanded Security Maintenance for Applications
        esm-infra       +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
        fips            +yes       +yes       +no           +NIST-certified core packages
        fips-updates    +yes       +yes       +no           +NIST-certified core packages with priority security updates
        livepatch       +yes       +yes       +yes          +Canonical Livepatch service
        usg             +yes       +yes       +no           +Security compliance and audit tools
        """

        Examples: ubuntu release
           | release |
           | focal   |

    @series.jammy
    @uses.config.machine_type.lxd.container
    @uses.config.contract_token_staging_expired
    Scenario Outline: Simulate status with expired token in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `sed -i 's/contracts.can/contracts.staging.can/' /etc/ubuntu-advantage/uaclient.conf` with sudo
        And I verify that a preflight check for `contract_token_staging_expired` formatted as json exits 1
        Then stdout is a json matching the `ua_status` schema
        And stdout matches regexp:
        """
        \"result\": \"failure\"
        """
        And stdout matches regexp:
        """
        \"message\": \"Contract .* expired on .*\"
        """
        When I verify that a preflight check for `contract_token_staging_expired` formatted as yaml exits 1
        Then stdout is a yaml matching the `ua_status` schema
        Then stdout matches regexp:
        """
        errors:
        - message: Contract .* expired on .*
        """
        When I verify that a preflight check for `contract_token_staging_expired` without the all flag exits 1
        Then stdout matches regexp:
        """
        This token is not valid.
        Contract \".*\" expired on .*

        SERVICE         +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
        esm-apps        +yes       +no        +no           +Expanded Security Maintenance for Applications
        esm-infra       +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
        livepatch       +yes       +yes       +yes          +Canonical Livepatch service
        """

        Examples: ubuntu release
           | release |
           | jammy   |
