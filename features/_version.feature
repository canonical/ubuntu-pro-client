Feature: Pro is expected version

    @uses.config.check_version
    Scenario Outline: Check pro version
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I run `dpkg-query --showformat='${Version}' --show ubuntu-advantage-tools` with sudo
        Then I will see the following on stdout
        """
        $behave_var{version}
        """
        When I run `pro version` with sudo
        Then I will see the following on stdout
        """
        $behave_var{version}
        """
        # The following doesn't actually assert anything. It merely ensures that the output of
        # apt-cache policy ubuntu-advantage-tools on the test machine is included in our test output.
        # This is useful to manually verify the package is installed from the correct source e.g. -proposed.
        When I check the apt-cache policy of ubuntu-advantage-tools
        Then the apt-cache policy of ubuntu-advantage-tools is
        """
        THIS GETS REPLACED AT RUNTIME VIA A HACK IN steps/ubuntu_advantage_tools.py
        """
        Examples: version
            | release | machine_type   |
            | xenial  | lxd-container  |
            | xenial  | lxd-vm         |
            | xenial  | aws.generic    |
            | xenial  | aws.pro        |
            | xenial  | aws.pro-fips   |
            | xenial  | azure.generic  |
            | xenial  | azure.pro      |
            | xenial  | azure.pro-fips |
            | xenial  | gcp.generic    |
            | xenial  | gcp.pro        |
            | xenial  | gcp.pro-fips   |
            | bionic  | lxd-container  |
            | bionic  | lxd-vm         |
            | bionic  | aws.generic    |
            | bionic  | aws.pro        |
            | bionic  | aws.pro-fips   |
            | bionic  | azure.generic  |
            | bionic  | azure.pro      |
            | bionic  | azure.pro-fips |
            | bionic  | gcp.generic    |
            | bionic  | gcp.pro        |
            | bionic  | gcp.pro-fips   |
            | focal   | lxd-container  |
            | focal   | lxd-vm         |
            | focal   | aws.generic    |
            | focal   | aws.pro        |
            | focal   | aws.pro-fips   |
            | focal   | azure.generic  |
            | focal   | azure.pro      |
            | focal   | azure.pro-fips |
            | focal   | gcp.generic    |
            | focal   | gcp.pro        |
            | focal   | gcp.pro-fips   |
            | jammy   | lxd-container  |
            | jammy   | lxd-vm         |
            | jammy   | aws.generic    |
            | jammy   | aws.pro        |
            | jammy   | aws.pro-fips   |
            | jammy   | azure.generic  |
            | jammy   | azure.pro      |
            | jammy   | azure.pro-fips |
            | jammy   | gcp.generic    |
            | jammy   | gcp.pro        |
            | jammy   | gcp.pro-fips   |
            | mantic  | lxd-container  |
            | mantic  | lxd-vm         |
            | mantic  | aws.generic    |
            | mantic  | aws.pro        |
            | mantic  | aws.pro-fips   |
            | mantic  | azure.generic  |
            | mantic  | azure.pro      |
            | mantic  | azure.pro-fips |
            | mantic  | gcp.generic    |
            | mantic  | gcp.pro        |
            | mantic  | gcp.pro-fips   |

    @uses.config.check_version
    @upgrade
    Scenario Outline: Check pro version
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I run `dpkg-query --showformat='${Version}' --show ubuntu-advantage-tools` with sudo
        Then I will see the following on stdout
        """
        $behave_var{version}
        """
        When I run `pro version` with sudo
        Then I will see the following on stdout
        """
        $behave_var{version}
        """
        # The following doesn't actually assert anything. It merely ensures that the output of
        # apt-cache policy ubuntu-advantage-tools on the test machine is included in our test output.
        # This is useful to manually verify the package is installed from the correct source e.g. -proposed.
        When I check the apt-cache policy of ubuntu-advantage-tools
        Then the apt-cache policy of ubuntu-advantage-tools is
        """
        THIS GETS REPLACED AT RUNTIME VIA A HACK IN steps/ubuntu_advantage_tools.py
        """
        Examples: version
            | release | machine_type  |
            | xenial  | lxd-container |
            | bionic  | lxd-container |
            | focal   | lxd-container |
            | jammy   | lxd-container |
            | mantic  | lxd-container |
