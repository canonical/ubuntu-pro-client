@uses.config.contract_token
Feature: Upgrade between releases when uaclient is unattached

    @wip
    @slow
    @series.impish
    @uses.config.machine_type.lxd.container
    @upgrade
    Scenario Outline: Unattached upgrade across releases
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get dist-upgrade --assume-yes` with sudo
        # Some packages upgrade may require a reboot
        And I reboot the `<release>` machine
        And I create the file `/etc/update-manager/release-upgrades.d/ua-test.cfg` with the following
        """
        [Sources]
        AllowThirdParty=yes
        """
        And I run `do-release-upgrade <devel_release> --frontend DistUpgradeViewNonInteractive` `with sudo` and stdin `y\n`
        And I reboot the `<release>` machine
        And I run `lsb_release -cs` as non-root
        Then I will see the following on stdout:
        """
        <next_release>
        """
        And I verify that running `egrep "<release>|disabled" /etc/apt/sources.list.d/*` `as non-root` exits `2`
        And I will see the following on stdout:
        """
        """
        When I run `ua status` with sudo
        Then stdout matches regexp:
        """
        esm-infra +yes +UA Infra: Extended Security Maintenance \(ESM\)
        """
        When I attach `contract_token` with sudo
        Then stdout matches regexp:
        """
        esm-infra +yes +enabled
        """

        Examples: ubuntu release
        | release  | next_release |
        | impish   | jammy        |

   @slow
   @series.xenial
   @series.bionic
   @series.focal
   @uses.config.machine_type.lxd.container
   @upgrade
   Scenario Outline: Unattached upgrade across LTS releases
        Given a `<release>` machine with ubuntu-advantage-tools installed
        # update-manager-core requires ua < 28. Our tests that build the package will
        # generate ua with version 28. We are removing that package here to make sure
        # do-release-upgrade will be able to run
        When I run `apt remove update-manager-core -y` with sudo
        And I run `apt-get dist-upgrade --assume-yes` with sudo
        # Some packages upgrade may require a reboot
        And I reboot the `<release>` machine
        And I create the file `/etc/update-manager/release-upgrades.d/ua-test.cfg` with the following
        """
        [Sources]
        AllowThirdParty=yes
        """
        Then I verify that running `do-release-upgrade <devel_release> --frontend DistUpgradeViewNonInteractive` `with sudo` exits `0`
        When I reboot the `<release>` machine
        And I run `lsb_release -cs` as non-root
        Then I will see the following on stdout:
        """
        <next_release>
        """
        And I verify that running `egrep "<release>|disabled" /etc/apt/sources.list.d/*` `as non-root` exits `2`
        And I will see the following on stdout:
        """
        """
        When I run `ua status` with sudo
        Then stdout matches regexp:
        """
        esm-infra +yes +UA Infra: Extended Security Maintenance \(ESM\)
        """
        When I attach `contract_token` with sudo
        Then stdout matches regexp:
        """
        esm-infra +yes +enabled
        """
        When I run `ua disable esm-infra` with sudo
        And I run `ua status` with sudo
        Then stdout matches regexp:
        """
        esm-infra +yes +disabled
        """

        Examples: ubuntu release
        | release | next_release | devel_release   |
        | xenial  | bionic       |                 |
        | bionic  | focal        |                 |
        | focal   | jammy        | --devel-release |
