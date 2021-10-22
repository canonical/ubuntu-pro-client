@uses.config.contract_token
Feature: Attached status

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached status in a ubuntu machine - formatted
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua status --format json` as non-root
        Then stdout is formatted as `json` and has keys:
            """
            _doc _schema_version account attached config config_path contract effective
            environment_vars execution_details execution_status expires machine_id notices
            services version
            """
        When I run `ua status --format yaml` as non-root
        Then stdout is formatted as `yaml` and has keys:
            """
            _doc _schema_version account attached config config_path contract effective
            environment_vars execution_details execution_status expires machine_id notices
            services version
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | xenial  |
           | hirsute |
           | impish  |
