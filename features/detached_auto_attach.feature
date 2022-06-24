@uses.config.contract_token
Feature: Attached cloud does not detach when auto-attaching after manually attaching

    @series.all
    @uses.config.machine_type.aws.generic
    @uses.config.machine_type.azure.generic
    @uses.config.machine_type.gcp.generic
    Scenario Outline: No detaching on manually attached machine on all clouds
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua refresh` with sudo
        Then I will see the following on stdout:
        """
        Successfully processed your ua configuration.
        Successfully refreshed your subscription.
        Successfully updated UA related APT and MOTD messages.
        """
        When I run `ua auto-attach` with sudo
        Then stderr matches regexp:
        """
        Skipping attach: Instance '[0-9a-z\-]+' is already attached.
        """
        When I run `ua status` with sudo
        Then stdout matches regexp:
        """
        esm-infra    +yes      +<esm-service> +Extended Security Maintenance for Infrastructure
        """

        Examples: ubuntu release
           | release | esm-service |
           | bionic  | enabled     |
           | focal   | enabled     |
           | xenial  | enabled     |
