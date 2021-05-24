Feature: Unattached status

    @series.all
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
           | focal   | yes      | no     | yes | no   | no          | yes   | yes       |
           | xenial  | yes      | yes    | yes | yes  | yes         | yes   | yes       |
           | groovy  | no       | no     | no  | no   | no          | no    | no        |
           | hirsute | no       | no     | no  | no   | no          | no    | no        |
