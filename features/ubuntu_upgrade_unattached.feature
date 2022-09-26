@uses.config.contract_token
Feature: Upgrade between releases when uaclient is unattached

    @slow
    @series.all
    @uses.config.machine_type.lxd.container
    @upgrade
    Scenario Outline: Unattached upgrade
        Given a `<release>` machine with ubuntu-advantage-tools installed
        # Local PPAs are prepared and served only when testing with local debs
        When I prepare the local PPAs to upgrade from `<release>` to `<next_release>`
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
        When I attach `contract_token` with sudo
        And I run `pro status --all` with sudo
        Then stdout matches regexp:
        """
        esm-infra +yes +<service_status>
        """

        Examples: ubuntu release
        | release | next_release | prompt | devel_release   | service_status |
        | xenial  | bionic       | lts    |                 | enabled        |
        | bionic  | focal        | lts    |                 | enabled        |
        | focal   | jammy        | lts    | --devel-release | enabled        |
        | jammy   | kinetic      | normal | --devel-release | n/a            |
