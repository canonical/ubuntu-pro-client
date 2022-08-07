@uses.config.contract_token
Feature: Attached status

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached status in a ubuntu machine - formatted
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `pro status --format json` as non-root
        Then stdout is a json matching the `ua_status` schema
        When I run `pro status --format yaml` as non-root
        Then stdout is a yaml matching the `ua_status` schema

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | xenial  |
           | jammy   |
           | kinetic |
