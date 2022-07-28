@uses.config.contract_token
Feature: Attached cloud does not detach when auto-attaching after manually attaching

    @series.all
    @uses.config.machine_type.aws.generic
    @uses.config.machine_type.azure.generic
    @uses.config.machine_type.gcp.generic
    Scenario Outline: No detaching on manually attached machine on all clouds
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `pro refresh` with sudo
        Then I will see the following on stdout:
        """
        Successfully processed your pro configuration.
        Successfully refreshed your subscription.
        Successfully updated Ubuntu Pro related APT and MOTD messages.
        """
        When I run `pro auto-attach` with sudo
        Then stderr matches regexp:
        """
        Skipping auto-attach: Instance is already attached.
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        esm-infra    +yes      +<esm-service> +Extended Security Maintenance for Infrastructure
        """

        Examples: ubuntu release
           | release | esm-service |
           | bionic  | enabled     |
           | focal   | enabled     |
           | xenial  | enabled     |
