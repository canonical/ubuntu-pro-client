@uses.config.contract_token
Feature: Upgrade between releases when uaclient is attached

    @slow
    @series.all
    @uses.config.machine_type.lxd-container
    @upgrade
    Scenario Outline: Attached upgrade
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `<before_cmd>` with sudo
        # Local PPAs are prepared and served only when testing with local debs
        And I prepare the local PPAs to upgrade from `<release>` to `<next_release>`
        And I run `apt-get dist-upgrade --assume-yes` with sudo
        # Some packages upgrade may require a reboot
        And I reboot the machine
        And I create the file `/etc/update-manager/release-upgrades.d/ua-test.cfg` with the following
        """
        [Sources]
        AllowThirdParty=yes
        """
        And I run `sed -i 's/Prompt=lts/Prompt=<prompt>/' /etc/update-manager/release-upgrades` with sudo
        And I run `do-release-upgrade <devel_release> --frontend DistUpgradeViewNonInteractive` `with sudo` and stdin `y\n`
        And I reboot the machine
        And I run `lsb_release -cs` as non-root
        Then I will see the following on stdout:
        """
        <next_release>
        """
        And I verify that running `egrep "<release>|disabled" /etc/apt/sources.list.d/*` `as non-root` exits `2`
        And I will see the following on stdout:
        """
        """
        When I run `pro refresh` with sudo
        And I run `pro status --all` with sudo
        Then stdout matches regexp:
        """
        <service1> +yes +<service1_status>
        """
        Then stdout matches regexp:
        """
        <service2> +yes +<service2_status>
        """
        When I run `pro detach --assume-yes` with sudo
        Then stdout matches regexp:
        """
        This machine is now detached.
        """

        Examples: ubuntu release
        | release | next_release | prompt | devel_release   | service1  | service1_status | service2 | service2_status | before_cmd     |
        | xenial  | bionic       | lts    |                 | esm-infra | enabled         | esm-apps | enabled         | true           |
        | bionic  | focal        | lts    |                 | esm-infra | enabled         | esm-apps | enabled         | true           |
        | bionic  | focal        | lts    |                 | usg       | enabled         | usg      | enabled         | pro enable cis |
        | focal   | jammy        | lts    | --devel-release | esm-infra | enabled         | esm-apps | enabled         | true           |
        | jammy   | lunar        | normal |                 | esm-infra | n/a             | esm-apps | n/a             | true           |
        | lunar   | mantic       | normal | --devel-release | esm-infra | n/a             | esm-apps | n/a             | true           |

    @slow
    @series.xenial
    @uses.config.machine_type.lxd-vm
    @upgrade
    Scenario Outline: Attached FIPS upgrade across LTS releases
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `apt-get install lsof` with sudo, retrying exit [100]
        And I run `pro disable livepatch` with sudo
        And I run `pro enable <fips-service> --assume-yes` with sudo
        Then stdout matches regexp:
        """
        Updating package lists
        Installing <fips-name> packages
        <fips-name> enabled
        A reboot is required to complete install
        """
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
        """
        <fips-service> +yes                enabled
        """
        And I verify that running `apt update` `with sudo` exits `0`
        When I reboot the machine
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
         # Local PPAs are prepared and served only when testing with local debs
        When I prepare the local PPAs to upgrade from `<release>` to `<next_release>`
        And I run `apt-get dist-upgrade -y --allow-downgrades` with sudo
        # A package may need a reboot after running dist-upgrade
        And I reboot the machine
        And I create the file `/etc/update-manager/release-upgrades.d/ua-test.cfg` with the following
        """
        [Sources]
        AllowThirdParty=yes
        """
        Then I verify that running `do-release-upgrade --frontend DistUpgradeViewNonInteractive` `with sudo` exits `0`
        When I reboot the machine
        And I run `lsb_release -cs` as non-root
        Then I will see the following on stdout:
        """
        <next_release>
        """
        When I verify that running `egrep "disabled" /etc/apt/sources.list.d/<source-file>.list` `as non-root` exits `1`
        Then I will see the following on stdout:
        """
        """
        When I run `pro status --all` with sudo
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
