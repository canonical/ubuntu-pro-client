Feature: Unattached status

    @series.trusty
    Scenario: Unattached status in a trusty lxd container
        Given a `trusty` lxd container with ubuntu-advantage-tools installed
        When I run `ua status` as non-root
        Then I will see the following on stdout:
            """
            SERVICE       AVAILABLE  DESCRIPTION
            cc-eal        no         Common Criteria EAL2 Provisioning Packages
            esm-apps      no         UA Apps: Extended Security Maintenance
            esm-infra     yes        UA Infra: Extended Security Maintenance
            fips          no         NIST-certified FIPS modules
            fips-updates  no         Uncertified security updates to FIPS modules
            livepatch     yes        Canonical Livepatch service

            This machine is not attached to a UA subscription.
            See https://ubuntu.com/advantage
            """
        When I run `ua status` with sudo
        Then I will see the following on stdout:
            """
            SERVICE       AVAILABLE  DESCRIPTION
            cc-eal        no         Common Criteria EAL2 Provisioning Packages
            esm-apps      no         UA Apps: Extended Security Maintenance
            esm-infra     yes        UA Infra: Extended Security Maintenance
            fips          no         NIST-certified FIPS modules
            fips-updates  no         Uncertified security updates to FIPS modules
            livepatch     yes        Canonical Livepatch service

            This machine is not attached to a UA subscription.
            See https://ubuntu.com/advantage
            """
