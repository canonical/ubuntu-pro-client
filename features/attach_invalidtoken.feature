Feature: Command behaviour when trying to attach a machine to an Ubuntu
         Advantage subscription using an invalid token

    @series.all
    Scenario Outline: Attach command in a machine
       Given a `<release>` machine with ubuntu-advantage-tools installed
        When I verify that running `ua attach INVALID_TOKEN` `with sudo` exits `1`
        Then stderr matches regexp:
            """
            Invalid token. See https://ubuntu.com/advantage
            """
        When I verify that running `ua attach INVALID_TOKEN` `as non-root` exits `1`
        Then I will see the following on stderr:
             """
             This command must be run as root (try using sudo)
             """
        Examples: ubuntu release
           | release |
           | trusty  |
           | xenial  |
           | bionic  |
           | focal   |
