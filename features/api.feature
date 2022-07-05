Feature: Client behaviour for the API endpoints

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: API invalid endpoint or args
    Given a `<release>` machine with ubuntu-advantage-tools installed
    When I verify that running `pro api invalid.endpoint` `with sudo` exits `1`
    Then stdout matches regexp:
    """
    {\"_schema_version\": \"v1\", \"data\": {}, \"errors\": \[{\"code\": \"invalid\-endpoint", \"meta\": {}, \"title\": \"'invalid\.endpoint' is not a valid endpoint\"}], \"result\": \"failure\", \"version\": \".*\", \"warnings\": \[]}
    """
    When I verify that running `pro api u.pro.version.v1 --args extra=arg` `with sudo` exits `1`
    Then stdout matches regexp:
    """
    {\"_schema_version\": \"v1\", \"data\": {}, \"errors\": \[{\"code\": \"no\-argument\-for\-endpoint\", \"meta\": {}, \"title\": \"u\.pro\.version\.v1 accepts no arguments\"}], \"result\": \"failure\", \"version\": \".*\", \"warnings\": \[]}
    """

    Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | xenial  |
           | impish  |
           | jammy   |

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Version v1 endpoint
    Given a `<release>` machine with ubuntu-advantage-tools installed
    When I run `pro api u.pro.version.v1` with sudo
    Then stdout matches regexp:
    """
    {\"_schema_version\": \"v1\", \"data\": {\"attributes\": {\"installed_version\": \".*\"}, \"meta\": {}, \"type\": \"Version\"}, \"errors\": \[], \"result\": \"success\", \"version\": \".*\", \"warnings\": \[]}
    """

    Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | xenial  |
           | impish  |
           | jammy   |
