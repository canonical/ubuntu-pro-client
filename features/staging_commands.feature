@uses.config.contract_token_staging
Feature: Enable command behaviour when attached to an UA staging subscription

    @series.xenial
    Scenario: Attached enable CC EAL service in a xenial lxd container
        Given a `xenial` lxd container with ubuntu-advantage-tools installed
        When I attach `contract_token_staging` with sudo
        And I run `ua enable cc-eal` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua enable cc-eal` with sudo
        Then I will see the following on stderr:
            """
            GPG key '/usr/share/keyrings/ubuntu-cc-keyring.gpg' not found
            """
