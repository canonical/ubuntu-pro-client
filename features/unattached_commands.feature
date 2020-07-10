Feature: Command behaviour when unattached

    @series.all
    Scenario Outline: Unattached auto-attach does nothing in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `ua auto-attach` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua auto-attach` with sudo
        Then stderr matches regexp:
            """
            Auto-attach image support is not available on <data>
            See: https://ubuntu.com/advantage
            """

        Examples: ubuntu release
           | release | data       |
           | trusty  | nocloudnet |
           | xenial  | lxd        |
           | bionic  | lxd        |
           | focal   | lxd        |

    @series.all
    Scenario Outline: Unattached commands that requires enabled user in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `ua <command>` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua <command>` with sudo
        Then stderr matches regexp:
            """
            This machine is not attached to a UA subscription.
            See https://ubuntu.com/advantage
            """

        Examples: ua commands
           | release | command |
           | trusty  | detach  |
           | trusty  | refresh |
           | xenial  | detach  |
           | xenial  | refresh |
           | bionic  | detach  |
           | bionic  | refresh |
           | focal   | detach  |
           | focal   | refresh |

    @series.all
    Scenario Outline: Unattached command known and unknown services in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `ua <command> livepatch` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua <command> <service>` with sudo
        Then stderr matches regexp:
            """
            To use '<service>' you need an Ubuntu Advantage subscription
            Personal and community subscriptions are available at no charge
            See https://ubuntu.com/advantage
            """

        Examples: ua commands
           | release | command  | service   |
           | trusty  | enable   | livepatch |
           | trusty  | disable  | livepatch |
           | trusty  | enable   | unknown   |
           | trusty  | disable  | unknown   |
           | xenial  | enable   | livepatch |
           | xenial  | disable  | livepatch |
           | xenial  | enable   | unknown   |
           | xenial  | disable  | unknown   |
           | bionic  | enable   | livepatch |
           | bionic  | disable  | livepatch |
           | bionic  | enable   | unknown   |
           | bionic  | disable  | unknown   |
           | focal   | enable   | livepatch |
           | focal   | disable  | livepatch |
           | focal   | enable   | unknown   |
           | focal   | disable  | unknown   |
