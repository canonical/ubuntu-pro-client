Feature: Unattached status

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Unattached status in a ubuntu machine - formatted
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `ua status --format json` as non-root
        Then stdout is a json matching the `ua_status` schema
        When I run `ua status --format yaml` as non-root
        Then stdout is a yaml matching the `ua_status` schema
        When I run `sed -i 's/contracts.can/invalidurl.notcan/' /etc/ubuntu-advantage/uaclient.conf` with sudo
        And I verify that running `ua status --format json` `as non-root` exits `1`
        Then stdout is a json matching the `ua_status` schema
        And I will see the following on stdout:
            """
            {"environment_vars": [], "errors": [{"message": "Failed to connect to authentication server\nCheck your Internet connection and try again.", "message_code": "connectivity-error", "service": null, "type": "system"}], "result": "failure", "services": [], "warnings": []}
            """
        And I verify that running `ua status --format yaml` `as non-root` exits `1`
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
           | impish  |
           | jammy   |

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Unattached status in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `ua status` as non-root
        Then stdout matches regexp:
            """
            SERVICE       +AVAILABLE  DESCRIPTION
            cc-eal        +<cc-eal>    +Common Criteria EAL2 Provisioning Packages
            ?<cis>( +<cis-available> +Security compliance and audit tools)?
            ?esm-apps      +<esm-apps>  +Extended Security Maintenance for Applications
            ?esm-infra     +<esm-infra>     +Extended Security Maintenance for Infrastructure
            fips          +<fips>      +NIST-certified core packages
            fips-updates  +<fips>      +NIST-certified core packages with priority security updates
            livepatch     +<livepatch> +Canonical Livepatch service
            ?<usg>( +<cis-available> +Security compliance and audit tools)?

            This machine is not attached to a UA subscription.
            See https://ubuntu.com/advantage
            """
        When I run `ua status --all` as non-root
        Then stdout matches regexp:
            """
            SERVICE       +AVAILABLE  DESCRIPTION
            cc-eal        +<cc-eal>    +Common Criteria EAL2 Provisioning Packages
            ?<cis>( +<cis-available> +Security compliance and audit tools)?
            ?esm-apps     +<esm-apps>  +Extended Security Maintenance for Applications
            esm-infra     +<esm-infra>     +Extended Security Maintenance for Infrastructure
            fips          +<fips>      +NIST-certified core packages
            fips-updates  +<fips>      +NIST-certified core packages with priority security updates
            livepatch     +<livepatch> +Canonical Livepatch service
            realtime-kernel +<realtime-kernel> +Beta-version Ubuntu Kernel with PREEMPT_RT patches
            ros           +<ros>       +Security Updates for the Robot Operating System
            ros-updates   +<ros>       +All Updates for the Robot Operating System
            ?<usg>( +<cis-available> +Security compliance and audit tools)?

            This machine is not attached to a UA subscription.
            See https://ubuntu.com/advantage
            """
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            SERVICE       +AVAILABLE  DESCRIPTION
            cc-eal        +<cc-eal>    +Common Criteria EAL2 Provisioning Packages
            ?<cis>( +<cis-available> +Security compliance and audit tools)?
            ?esm-apps      +<esm-apps>  +Extended Security Maintenance for Applications
            ?esm-infra     +<esm-infra>     +Extended Security Maintenance for Infrastructure
            fips          +<fips>      +NIST-certified core packages
            fips-updates  +<fips>      +NIST-certified core packages with priority security updates
            livepatch     +<livepatch> +Canonical Livepatch service
            ?<usg>( +<cis-available> +Security compliance and audit tools)?

            This machine is not attached to a UA subscription.
            See https://ubuntu.com/advantage
            """
        When I run `ua status --all` with sudo
        Then stdout matches regexp:
            """
            SERVICE       +AVAILABLE  DESCRIPTION
            cc-eal        +<cc-eal>    +Common Criteria EAL2 Provisioning Packages
            ?<cis>( +<cis-available> +Security compliance and audit tools)?
            ?esm-apps      +<esm-apps>  +Extended Security Maintenance for Applications
            esm-infra     +<esm-infra>     +Extended Security Maintenance for Infrastructure
            fips          +<fips>      +NIST-certified core packages
            fips-updates  +<fips>      +NIST-certified core packages with priority security updates
            livepatch     +<livepatch> +Canonical Livepatch service
            realtime-kernel +<realtime-kernel> +Beta-version Ubuntu Kernel with PREEMPT_RT patches
            ros           +<ros>       +Security Updates for the Robot Operating System
            ros-updates   +<ros>       +All Updates for the Robot Operating System
            ?<usg>( +<cis-available> +Security compliance and audit tools)?

            This machine is not attached to a UA subscription.
            See https://ubuntu.com/advantage
            """ 
        When I append the following on uaclient config:
            """
            features:
              allow_beta: true
            """
        And I run `ua status` as non-root
        Then stdout matches regexp:
            """
            SERVICE       +AVAILABLE  DESCRIPTION
            cc-eal        +<cc-eal>    +Common Criteria EAL2 Provisioning Packages
            ?<cis>( +<cis-available> +Security compliance and audit tools)?
            ?esm-apps      +<esm-apps>  +Extended Security Maintenance for Applications
            esm-infra     +<esm-infra>     +Extended Security Maintenance for Infrastructure
            fips          +<fips>      +NIST-certified core packages
            fips-updates  +<fips>      +NIST-certified core packages with priority security updates
            livepatch     +<livepatch> +Canonical Livepatch service
            realtime-kernel +<realtime-kernel> +Beta-version Ubuntu Kernel with PREEMPT_RT patches
            ros           +<ros>       +Security Updates for the Robot Operating System
            ros-updates   +<ros>       +All Updates for the Robot Operating System
            ?<usg>( +<cis-available> +Security compliance and audit tools)?

            FEATURES
            allow_beta: True

            This machine is not attached to a UA subscription.
            See https://ubuntu.com/advantage
            """ 

        Examples: ubuntu release
           | release | esm-apps | cc-eal | cis | cis-available | fips | esm-infra | ros | livepatch | usg | realtime-kernel |
           | xenial  | yes      | yes    | cis | yes           | yes  | yes       | yes | yes       |     | no              |
           | bionic  | yes      | yes    | cis | yes           | yes  | yes       | yes | yes       |     | no              |
           | focal   | yes      | no     |     | yes           | yes  | yes       | no  | yes       | usg | no              |
           | impish  | no       | no     | cis | no            | no   | no        | no  | no        |     | no              |
           | jammy   | yes      | no     |     | no            | no   | yes       | no  | yes       | usg | yes             |

    @series.all
    @uses.config.machine_type.lxd.container
    @uses.config.contract_token
    Scenario Outline: Simulate status in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I do a preflight check for `contract_token` without the all flag
        Then stdout matches regexp:
            """
            SERVICE       +AVAILABLE  ENTITLED   AUTO_ENABLED  DESCRIPTION
            cc-eal        +<cc-eal>    +yes  +no   +Common Criteria EAL2 Provisioning Packages
            ?<cis>( +<cis-available> +yes +no +Security compliance and audit tools)?
            ?esm-apps      +<esm-apps>  +Extended Security Maintenance for Applications
            ?esm-infra     +<esm-infra> +yes  +yes  +Extended Security Maintenance for Infrastructure
            fips          +<fips>      +yes  +no   +NIST-certified core packages
            fips-updates  +<fips>      +yes  +no   +NIST-certified core packages with priority security updates
            livepatch     +<livepatch> +yes  +yes  +Canonical Livepatch service
            ?<usg>( +<cis-available> +yes +no +Security compliance and audit tools)?
            """
        When I do a preflight check for `contract_token` with the all flag
        Then stdout matches regexp:
            """
            SERVICE       +AVAILABLE  ENTITLED   AUTO_ENABLED  DESCRIPTION
            cc-eal        +<cc-eal>    +yes  +no   +Common Criteria EAL2 Provisioning Packages
            ?<cis>( +<cis-available> +yes +no +Security compliance and audit tools)?
            ?esm-apps      +<esm-apps>  +yes  +yes  +Extended Security Maintenance for Applications
            esm-infra     +<esm-infra> +yes  +yes  +Extended Security Maintenance for Infrastructure
            fips          +<fips>      +yes  +no   +NIST-certified core packages
            fips-updates  +<fips>      +yes  +no   +NIST-certified core packages with priority security updates
            livepatch     +<livepatch> +yes  +yes  +Canonical Livepatch service
            realtime-kernel +<realtime-kernel> +yes  +no  +Beta-version Ubuntu Kernel with PREEMPT_RT patches
            ros           +<ros>       +yes  +no   +Security Updates for the Robot Operating System
            ros-updates   +<ros>       +yes  +no   +All Updates for the Robot Operating System
            ?<usg>( +<cis-available> +yes +no +Security compliance and audit tools)?
            """
        When I do a preflight check for `contract_token` formatted as json
        Then stdout is a json matching the `ua_status` schema
        When I do a preflight check for `contract_token` formatted as yaml
        Then stdout is a yaml matching the `ua_status` schema
        When I verify that a preflight check for `invalid_token` formatted as json exits 1
        Then stdout is a json matching the `ua_status` schema
        And I will see the following on stdout:
            """
            {"environment_vars": [], "errors": [{"message": "Invalid token. See https://ubuntu.com/advantage", "message_code": "attach-invalid-token", "service": null, "type": "system"}], "result": "failure", "services": [], "warnings": []}
            """
        When I verify that a preflight check for `invalid_token` formatted as yaml exits 1
        Then stdout is a yaml matching the `ua_status` schema
        And I will see the following on stdout:
            """
            environment_vars: []
            errors:
            - message: Invalid token. See https://ubuntu.com/advantage
              message_code: attach-invalid-token
              service: null
              type: system
            result: failure
            services: []
            warnings: []
            """
        Examples: ubuntu release
           | release | esm-apps | cc-eal | cis | cis-available | fips | esm-infra | ros | livepatch | usg | realtime-kernel |
           | xenial  | yes      | yes    | cis | yes           | yes  | yes       | yes | yes       |     | no              |
           | bionic  | yes      | yes    | cis | yes           | yes  | yes       | yes | yes       |     | no              |
           | focal   | yes      | no     |     | yes           | yes  | yes       | no  | yes       | usg | no              |
           | impish  | no       | no     | cis | no            | no   | no        | no  | no        |     | no              |
           | jammy   | yes      | no     |     | no            | no   | yes       | no  | yes       | usg | yes             |


    @series.all
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

            SERVICE       +AVAILABLE  ENTITLED   AUTO_ENABLED  DESCRIPTION
            cc-eal        +<cc-eal>    +yes  +no   +Common Criteria EAL2 Provisioning Packages
            ?<cis>( +<cis-available> +yes +no +Security compliance and audit tools)?
            ?esm-apps      +<esm-apps>  +Extended Security Maintenance for Applications
            ?esm-infra     +<esm-infra> +yes  +yes  +Extended Security Maintenance for Infrastructure
            fips          +<fips>      +yes  +no   +NIST-certified core packages
            fips-updates  +<fips>      +yes  +no   +NIST-certified core packages with priority security updates
            livepatch     +<livepatch> +yes  +yes  +Canonical Livepatch service
            ?<usg>( +<cis-available> +yes +no +Security compliance and audit tools)?
            """

        Examples: ubuntu release
           | release | esm-apps | cc-eal | cis | cis-available | fips | esm-infra | ros | livepatch | usg |
           | xenial  | yes      | yes    | cis | yes           | yes  | yes       | yes | yes       |     |
           | bionic  | yes      | yes    | cis | yes           | yes  | yes       | yes | yes       |     |
           | focal   | yes      | no     |     | yes           | yes  | yes       | no  | yes       | usg |
           | impish  | no       | no     | cis | no            | no   | no        | no  | no        |     |
           | jammy   | yes      | no     |     | no            | no   | yes       | no  | yes       | usg |
