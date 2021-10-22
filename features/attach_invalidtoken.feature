Feature: Command behaviour when trying to attach a machine to an Ubuntu
         Advantage subscription using an invalid token

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attach command failure on invalid token
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I verify that running `ua attach INVALID_TOKEN` `with sudo` exits `1`
        Then stderr matches regexp:
            """
            Invalid token. See https://ubuntu.com/advantage
            """
        When I verify that running `ua attach INVALID_TOKEN` `as non-root` exits `1`
        Then I will see the following on stderr:
             """
             This command must be run as root (try using sudo).
             """
        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | hirsute |
           | impish |

    @uses.config.contract_token_staging_expired
    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attach command failure on expired token
       Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attempt to attach `contract_token_staging_expired` with sudo
        Then stderr matches regexp:
             """
             Attach denied:
             Contract ".*" .*
             Visit https://ubuntu.com/advantage to manage contract tokens.
             """
        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | hirsute |
           | impish |
