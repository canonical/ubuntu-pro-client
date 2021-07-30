Feature: UA post-install script checks

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Do not fail on postinst when cloud-id returns error
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I delete the file `/run/cloud-init/instance-data.json`
        Then I verify that running `dpkg-reconfigure ubuntu-advantage-tools` `with sudo` exits `0`

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | hirsute |
