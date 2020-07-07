Feature: Command behaviour when trying to attach a machine to an Ubuntu
         Advantage subscription using an invalid token

    @series.all
    Scenario Outline: Attach command in a machine
       Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `ua attach INVALID_TOKEN` with sudo
        Then stderr matches regexp:
            """
            Invalid token. See https://ubuntu.com/advantage
            """
        When I run `ua attach INVALID_TOKEN` as non-root
        Then I will see the following on stderr:
             """
             This command must be run as root (try using sudo)
             """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | trusty  |
           | xenial  |
