@uses.config.contract_token
Feature: Upgrade between releases when uaclient is unattached

    @series.focal
    @series.hirsute
    @upgrade
    Scenario Outline: Unattached upgrade across LTS releases
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get dist-upgrade --assume-yes` with sudo
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
        esm-infra     no       +UA Infra: Extended Security Maintenance \(ESM\)
        """
        When I attach `contract_token` with sudo
        Then stdout matches regexp:
        """
        esm-infra     yes         +n/a
        """

        Examples: ubuntu release
        | release  | next_release | devel_release   |
        | focal    | groovy       |                 |
        | hirsute  | impish       | --devel-release |

   @series.xenial
   @series.bionic
   @upgrade
   Scenario Outline: Unattached upgrade across LTS releases
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get dist-upgrade --assume-yes` with sudo
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
        SERVICE       AVAILABLE  DESCRIPTION
        cis           yes      +Center for Internet Security Audit Tools
        esm-infra     yes      +UA Infra: Extended Security Maintenance \(ESM\)
        """
        When I attach `contract_token` with sudo
        Then stdout matches regexp:
        """
        esm-infra     yes            +enabled
        """
        When I run `ua disable esm-infra` with sudo
        And I run `ua status` with sudo
        Then stdout matches regexp:
        """
        esm-infra     yes            +disabled
        """

        Examples: ubuntu release
        | release | next_release |
        | xenial  | bionic       |
        | bionic  | focal        |
