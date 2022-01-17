Feature: UA is expected version

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
    Scenario Outline: Check ua version
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `dpkg-query --showformat='${Version}' --show ubuntu-advantage-tools` with sudo
        Then stdout matches regexp:
        """
        {UACLIENT_BEHAVE_CHECK_VERSION}
        """
        When I run `ua version` with sudo
        Then stdout matches regexp:
        # We are adding that regex here to match possible config overrides
        # we add. For example, on PRO machines we add a config override to
        # disable auto-attach on boot
        """
        {UACLIENT_BEHAVE_CHECK_VERSION}.*
        """
        Examples: version
            | release |
            | xenial  |
            | bionic  |
            | focal   |
            | hirsute |
            | impish  |
            | jammy   |

    @series.all
    @uses.config.check_version
    @uses.config.machine_type.lxd.container
    @upgrade
    Scenario Outline: Check ua version
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `dpkg-query --showformat='${Version}' --show ubuntu-advantage-tools` with sudo
        Then I will see the following on stdout
        """
        {UACLIENT_BEHAVE_CHECK_VERSION}
        """
        When I run `ua version` with sudo
        Then stdout matches regexp:
        # We are adding that regex here to match possible config overrides
        # we add. For example, on PRO machines we add a config override to
        # disable auto-attach on boot
        """
        {UACLIENT_BEHAVE_CHECK_VERSION}.*
        """
        Examples: version
            | release |
            | xenial  |
            | bionic  |
            | focal   |
            | hirsute |
            | impish  |
