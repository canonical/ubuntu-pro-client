@uses.config.contract_token
Feature: Command behaviour when attaching a machine to an Ubuntu Advantage
        subscription using a valid token

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attach command in a ubuntu lxd container
       Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then stdout matches regexp:
        """
        ESM Infra enabled
        """
        And stdout matches regexp:
        """
        This machine is now attached to
        """
        And stdout matches regexp:
        """
        SERVICE       ENTITLED  STATUS    DESCRIPTION
        esm-apps     +no       +—        +UA Apps: Extended Security Maintenance
        esm-infra    +yes      +enabled  +UA Infra: Extended Security Maintenance
        livepatch    +yes      +n/a      +Canonical Livepatch service
        """
        And stderr matches regexp:
        """
        Enabling default service esm-infra
        """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | trusty  |
           | xenial  |
