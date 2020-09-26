@uses.config.contract_token
Feature: Command behaviour when attaching a machine to an Ubuntu Advantage
        subscription using a valid token

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attach command in a ubuntu lxd container
       Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get install -y <downrev_pkg>` with sudo
        And I run `/usr/lib/update-notifier/apt-check  --human-readable` as non-root

        Then if `<release>` in `trusty` and stdout matches regexp:
        """
        UA Infrastructure Extended Security Maintenance \(ESM\) is not enabled.

        \d+ update(s)? can be installed immediately.
        \d+ of these updates (is a|are) security update(s)?.

        Enable UA Infrastructure ESM to receive \d+ additional security update(s)?.
        See https://ubuntu.com/advantage or run: sudo ua status
        """
        Then if `<release>` in `xenial or bionic` and stdout matches regexp:
        """
        \d+ packages can be updated.
        \d+ updates are security updates.
        """
        Then if `<release>` in `focal` and stdout matches regexp:
        """
        \d+ update(s)? can be installed immediately.
        \d+ of these updates (is a|are) security update(s)?.
        """
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
        When I run `/usr/lib/update-notifier/apt-check  --human-readable` as non-root
        Then if `<release>` in `trusty or focal` and stdout matches regexp:
        """
        UA Infrastructure Extended Security Maintenance \(ESM\) is enabled.

        \d+ update(s)? can be installed immediately.
        \d+ of these updates (is|are) provided through UA Infrastructure ESM.
        \d+ of these updates (is a|are) security update(s)?.
        To see these additional updates run: apt list --upgradable
        """
        Then if `<release>` in `xenial or bionic` and stdout matches regexp:
        """
        \d+ packages can be updated.
        \d+ updates are security updates.
        """
        Examples: ubuntu release packages
           | release | downrev_pkg                     |
           | trusty  | libgit2-0=0.19.0-2ubuntu0.4     |
           | xenial  | libkrad0=1.13.2+dfsg-5ubuntu2.1 |
           | bionic  | libkrad0=1.16-2ubuntu0.1        |
           | focal   | hello=2.10-2ubuntu2             |

    @series.all
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

    @series.all
    @uses.config.machine_type.azure.generic
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
           | trusty  | disabled  | Canonical Livepatch service   |
           | xenial  | n/a       | Canonical Livepatch service   |
           | bionic  | n/a       | Canonical Livepatch service   |
           | focal   | n/a       | Canonical Livepatch service   |
