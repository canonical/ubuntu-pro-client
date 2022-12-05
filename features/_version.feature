Feature: Pro is expected version

    @series.all
    @uses.config.check_version
    @uses.config.machine_type.lxd.container
    @uses.config.machine_type.lxd.vm
    @uses.config.machine_type.aws.generic
    @uses.config.machine_type.aws.pro
    @uses.config.machine_type.aws.pro.fips
    @uses.config.machine_type.azure.generic
    @uses.config.machine_type.azure.pro
    @uses.config.machine_type.azure.pro.fips
    @uses.config.machine_type.gcp.generic
    @uses.config.machine_type.gcp.pro
    @uses.config.machine_type.gcp.pro.fips
    Scenario Outline: Check pro version
        Given a `<release>` machine with ubuntu-advantage-tools installed
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
        Examples: version
            | release |
            | xenial  |
            | bionic  |
            | focal   |
            | jammy   |
            | kinetic |

    @series.all
    @uses.config.check_version
    @uses.config.machine_type.lxd.container
    @upgrade
    Scenario Outline: Check pro version
        Given a `<release>` machine with ubuntu-advantage-tools installed
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
        Examples: version
            | release |
            | xenial  |
            | bionic  |
            | focal   |
            | jammy   |
            | kinetic |
