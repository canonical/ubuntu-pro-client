@uses.config.contract_token
Feature: Timer for regular background jobs while attached

    # earlies, latest lts, devel
    @series.xenial
    @series.jammy
    @series.mantic
    @uses.config.machine_type.lxd.container
    Scenario Outline: Timer is stopped when detached, started when attached
        Given a `<release>` machine with ubuntu-advantage-tools installed
        Then I verify the `ua-timer` systemd timer is disabled
        When I attach `contract_token` with sudo
        # 6 hour timer with 1 hour randomized delay -> potentially 7 hours
        Then I verify the `ua-timer` systemd timer is scheduled to run within `420` minutes
        When I run `pro detach --assume-yes` with sudo
        Then I verify the `ua-timer` systemd timer is disabled
        Examples: ubuntu release
            | release |
            | xenial  |
            | jammy   |
            | mantic  |
