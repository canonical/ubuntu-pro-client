Feature: Command behaviour when attaching a machine to an Ubuntu Advantage
        subscription using a valid token

    Scenario: Attach command in a trusty lxd container
       Given a trusty lxd container with ubuntu-advantage-tools installed
        When I attach "<contract_token>" with sudo
        Then stdout will include:
        """
        ESM Infra enabled
        """
        And stdout will include:
        """
        This machine is now attached to
        """
        And stdout will include:
        """
        SERVICE       ENTITLED  STATUS    DESCRIPTION
        cc-eal        yes       n/a       Common Criteria EAL2 Provisioning Packages
        cis-audit     no        —         Center for Internet Security Audit Tools
        esm-apps      no        —         UA Apps: Extended Security Maintenance
        esm-infra     yes       enabled   UA Infra: Extended Security Maintenance
        fips          yes       n/a       NIST-certified FIPS modules
        fips-updates  yes       n/a       Uncertified security updates to FIPS modules
        livepatch     yes       n/a       Canonical Livepatch service

        Enable services with: ua enable <service>
        """
        And I will see the following on stderr:
        """
        Enabling default service esm-infra
        """
