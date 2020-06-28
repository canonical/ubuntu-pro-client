Feature: Command behaviour when trying to attach a machine to an Ubuntu
         Advantage subscription using an invalid token

    @series.trusty
    Scenario: Attach command in a trusty machine
       Given a `trusty` machine with ubuntu-advantage-tools installed
        When I run `ua attach INVALID_TOKEN` with sudo
        Then I will see the following on stderr:
            """
            Invalid token. See https://ubuntu.com/advantage
            """
        When I run `ua attach INVALID_TOKEN` as non-root
        Then I will see the following on stderr:
             """
             This command must be run as root (try using sudo)
             """

    @series.focal
    Scenario: Attach command in a focal machine
       Given a `focal` machine with ubuntu-advantage-tools installed
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
