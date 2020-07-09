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
           | bionic  | lxd        |
           | focal   | lxd        |
           | trusty  | nocloudnet |
           | xenial  | lxd        |

    @series.trusty
    Scenario Outline: Unattached commands that requires enabled user in a trusty machine
        Given a `trusty` machine with ubuntu-advantage-tools installed
        When I run `ua <command>` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua <command>` with sudo
        Then I will see the following on stderr:
            """
            This machine is not attached to a UA subscription.
            See https://ubuntu.com/advantage
            """

        Examples: ua commands
           | command |
           | detach  |
           | refresh |

    @series.trusty
    Scenario Outline: Unattached command known and unknown services in a trusty machine
        Given a `trusty` machine with ubuntu-advantage-tools installed
        When I run `ua <command> livepatch` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua <command> <service>` with sudo
        Then I will see the following on stderr:
            """
            To use '<service>' you need an Ubuntu Advantage subscription
            Personal and community subscriptions are available at no charge
            See https://ubuntu.com/advantage
            """

        Examples: ua commands
           | command  | service   | 
           | enable   | livepatch |
           | disable  | livepatch |
           | enable   | unknown   |
           | disable  | unknown   |

    @series.focal
    Scenario Outline: Unattached commands that requires enabled user in a focal machine
        Given a `focal` machine with ubuntu-advantage-tools installed
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
           | command |
           | detach  |
           | refresh |


    @series.focal
    Scenario Outline: Unattached command of a known service in a focal machine
        Given a `focal` machine with ubuntu-advantage-tools installed
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
           | command | service   |
           | disable | livepatch |
           | enable  | livepatch |
           | disable | unknown   |
           | enable  | unknown   |
