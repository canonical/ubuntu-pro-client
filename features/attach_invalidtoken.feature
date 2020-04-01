Feature: Command behaviour when trying to attach a machine to an Ubuntu
         Advantage subscription using an invalid token

    @series.trusty
    Scenario: Attach command in a trusty lxd container
       Given a `trusty` lxd container with ubuntu-advantage-tools installed
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
