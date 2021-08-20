Feature: UA is expected version

    @series.all
    @uses.config.check_version
    @uses.config.machine_type.lxd.container
    @uses.config.machine_type.lxd.vm
    @uses.config.machine_type.aws.generic
    @uses.config.machine_type.aws.pro
    @uses.config.machine_type.azure.generic
    @uses.config.machine_type.azure.pro
    @uses.config.machine_type.gcp.generic
    @uses.config.machine_type.gcp.pro
    Scenario Outline: Check ua version
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `ua version` with sudo
        Then I will see the following on stdout
        """
        {UACLIENT_BEHAVE_CHECK_VERSION}
        """
        Examples: version
            | release |
            | xenial  |
            | bionic  |
            | focal   |
            | hirsute |

    @series.all
    @uses.config.check_version
    @uses.config.machine_type.lxd.container
    @upgrade
    Scenario Outline: Check ua version
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `ua version` with sudo
        Then I will see the following on stdout
        """
        {UACLIENT_BEHAVE_CHECK_VERSION}
        """
        Examples: version
            | release |
            | xenial  |
            | bionic  |
            | focal   |
            | hirsute |
