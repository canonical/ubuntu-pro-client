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

    @series.all
    @uses.config.machine_type.azure.generic
    @uses.config.machine_type.aws.generic
    @uses.config.machine_type.lxd.vm
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
        livepatch    +yes      +<lp_status>  +<lp_desc>
        """
        And stderr matches regexp:
        """
        Enabling default service esm-infra
        """

        Examples: ubuntu release livepatch status
           | release | lp_status | lp_desc                       |
           | trusty  | n/a       | Available with the HWE kernel |
           | xenial  | enabled   | Canonical Livepatch service   |
           | bionic  | enabled   | Canonical Livepatch service   |
           | focal   | enabled   | Canonical Livepatch service   |
