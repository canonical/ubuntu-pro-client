@uses.config.contract_token
Feature: Upgrade between releases when uaclient is attached

    @series.focal
    @series.hirsute
    @upgrade
    Scenario Outline: Attached upgrade across LTS releases
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `apt-get dist-upgrade --assume-yes` with sudo
        And I create the file `/etc/update-manager/release-upgrades.d/ua-test.cfg` with the following
        """
        [Sources]
        AllowThirdParty=yes
        """
        And I run `sed -i 's/Prompt=lts/Prompt=normal/' /etc/update-manager/release-upgrades` with sudo
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
        esm-infra     yes                n/a
        """
        When I run `ua detach --assume-yes` with sudo
        Then stdout matches regexp:
            """
            This machine is now detached.
            """

        Examples: ubuntu release
        | release | next_release | devel_release   | stdin |
        | focal   | groovy       |                 |       |
        | hirsute | impish       | --devel-release |  y\n  |

   @series.xenial
   @series.bionic
   @upgrade
   Scenario Outline: Attached upgrade across LTS releases
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `apt-get dist-upgrade --assume-yes` with sudo
        # Some packages upgrade may require a reboot
        And I reboot the `<release>` machine
        And I create the file `/etc/update-manager/release-upgrades.d/ua-test.cfg` with the following
        """
        [Sources]
        AllowThirdParty=yes
        """
        Then I verify that running `do-release-upgrade --frontend DistUpgradeViewNonInteractive` `with sudo` exits `0`
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
        esm-infra     yes                enabled
        """
        When I run `ua disable esm-infra` with sudo
        And I run `ua status` with sudo
        Then stdout matches regexp:
            """
            esm-infra    +yes      +disabled +UA Infra: Extended Security Maintenance \(ESM\)
            """

        Examples: ubuntu release
        | release | next_release |
        | xenial  | bionic       |
        | bionic  | focal        |
