Feature: Unattached status

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Unattached status in a ubuntu machine - formatted
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `ua status --format json` as non-root
        Then stdout is formatted as `json` and has keys:
            """
            _doc _schema_version account attached config config_path contract effective
            environment_vars execution_details execution_status expires machine_id notices
            services version
            """
        When I run `ua status --format yaml` as non-root
        Then stdout is formatted as `yaml` and has keys:
            """
            _doc _schema_version account attached config config_path contract effective
            environment_vars execution_details execution_status expires machine_id notices
            services version
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | xenial  |
           | hirsute |

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Unattached status in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `ua status` as non-root
        Then stdout matches regexp:
            """
            SERVICE       AVAILABLE  DESCRIPTION
            cis           <cis>       +Center for Internet Security Audit Tools
            esm-infra     <infra>     +UA Infra: Extended Security Maintenance \(ESM\)
            fips          <fips>      +NIST-certified core packages
            fips-updates  <fips>      +NIST-certified core packages with priority security updates
            livepatch     <livepatch> +Canonical Livepatch service

            This machine is not attached to a UA subscription.
            See https://ubuntu.com/advantage
            """
        When I run `ua status --all` as non-root
        Then stdout matches regexp:
            """
            SERVICE       AVAILABLE  DESCRIPTION
            cc-eal        <cc-eal>   +Common Criteria EAL2 Provisioning Packages
            cis           <cis>      +Center for Internet Security Audit Tools
            esm-apps      <esm-apps> +UA Apps: Extended Security Maintenance \(ESM\)
            esm-infra     <infra>    +UA Infra: Extended Security Maintenance \(ESM\)
            fips          <fips>     +NIST-certified core packages
            fips-updates  <fips>     +NIST-certified core packages with priority security updates
            livepatch     <livepatch> +Canonical Livepatch service

            This machine is not attached to a UA subscription.
            See https://ubuntu.com/advantage
            """
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            SERVICE       AVAILABLE  DESCRIPTION
            cis           <cis>       +Center for Internet Security Audit Tools
            esm-infra     <infra>     +UA Infra: Extended Security Maintenance \(ESM\)
            fips          <fips>      +NIST-certified core packages
            fips-updates  <fips>      +NIST-certified core packages with priority security updates
            livepatch     <livepatch> +Canonical Livepatch service

            This machine is not attached to a UA subscription.
            See https://ubuntu.com/advantage
            """
        When I run `ua status --all` with sudo
        Then stdout matches regexp:
            """
            SERVICE       AVAILABLE  DESCRIPTION
            cc-eal        <cc-eal>   +Common Criteria EAL2 Provisioning Packages
            cis           <cis>      +Center for Internet Security Audit Tools
            esm-apps      <esm-apps>  +UA Apps: Extended Security Maintenance \(ESM\)
            esm-infra     <infra>     +UA Infra: Extended Security Maintenance \(ESM\)
            fips          <fips>      +NIST-certified core packages
            fips-updates  <fips>      +NIST-certified core packages with priority security updates
            livepatch     <livepatch> +Canonical Livepatch service

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
            SERVICE       AVAILABLE  DESCRIPTION
            cc-eal        <cc-eal>    +Common Criteria EAL2 Provisioning Packages
            cis           <cis>      +Center for Internet Security Audit Tools
            esm-apps      <esm-apps>  +UA Apps: Extended Security Maintenance \(ESM\)
            esm-infra     <infra>     +UA Infra: Extended Security Maintenance \(ESM\)
            fips          <fips>      +NIST-certified core packages
            fips-updates  <fips>      +NIST-certified core packages with priority security updates
            livepatch     <livepatch> +Canonical Livepatch service

            This machine is not attached to a UA subscription.
            See https://ubuntu.com/advantage
            """ 

        Examples: ubuntu release
           | release | esm-apps | cc-eal | cis | fips | fips-update | infra | livepatch |
           | bionic  | yes      | no     | yes | yes  | yes         | yes   | yes       |
           | focal   | yes      | no     | yes | yes  | yes         | yes   | yes       |
           | xenial  | yes      | yes    | yes | yes  | yes         | yes   | yes       |
           | hirsute | no       | no     | no  | no   | no          | no    | no        |
