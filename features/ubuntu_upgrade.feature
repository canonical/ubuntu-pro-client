@uses.config.contract_token
Feature: Upgrade between releases when uaclient is attached

    @series.focal
    @series.hirsute
    @upgrade
    Scenario Outline: Attached upgrade across releases
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
        | release | next_release | devel_release   |
        | focal   | groovy       |                 |
        | hirsute | impish       | --devel-release |

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

    @series.xenial
    @uses.config.machine_type.lxd.vm
    Scenario Outline: Attached FIPS upgrade across LTS releases
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `apt-get install lsof` with sudo, retrying exit [100]
        And I run `ua disable livepatch` with sudo
        And I run `ua enable <fips-service> --assume-yes` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            Installing <fips-name> packages
            <fips-name> enabled
            A reboot is required to complete install
            """
        When I run `ua status --all` with sudo
        Then stdout matches regexp:
            """
            <fips-service> +yes                enabled
            """
        And I verify that running `apt update` `with sudo` exits `0`
        When I reboot the `<release>` machine
        And  I run `uname -r` as non-root
        Then stdout matches regexp:
        """
        fips
        """
        When I run `cat /proc/sys/crypto/fips_enabled` with sudo
        Then I will see the following on stdout:
        """
        1
        """
        When I run `apt-get dist-upgrade -y --allow-downgrades` with sudo
        # A package may need a reboot after running dist-upgrade
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
        When I verify that running `egrep "disabled" /etc/apt/sources.list.d/<source-file>.list` `as non-root` exits `1`
        Then I will see the following on stdout:
        """
        """
        When I run `ua status --all` with sudo
        Then stdout matches regexp:
        """
        <fips-service> +yes                enabled
        """
        When  I run `uname -r` as non-root
        Then stdout matches regexp:
            """
            fips
            """
        When I run `cat /proc/sys/crypto/fips_enabled` with sudo
        Then I will see the following on stdout:
        """
        1
        """

        Examples: ubuntu release
        | release | next_release | fips-service  | fips-name    | source-file         |
        | xenial  | bionic       | fips          | FIPS         | ubuntu-fips         |
        | xenial  | bionic       | fips-updates  | FIPS Updates | ubuntu-fips-updates |
