@uses.config.contract_token
Feature: Attached cloud does not detach when auto-attaching after manually attaching

    @series.lts
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
        When I verify that running `pro auto-attach` `with sudo` exits `2`
        Then stderr matches regexp:
        """
        This machine is already attached to 'UA Client Test'
        To use a different subscription first run: sudo pro detach.
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        esm-infra    +yes      +<esm-service> +Expanded Security Maintenance for Infrastructure
        """

        Examples: ubuntu release
           | release | esm-service |
           | bionic  | enabled     |
           | focal   | enabled     |
           | xenial  | enabled     |
