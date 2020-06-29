Feature: Command behaviour when unattached

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
    Scenario Outline: Unattached command of a known service in a trusty machine
        Given a `trusty` machine with ubuntu-advantage-tools installed
        When I run `ua <command> livepatch` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua <command> livepatch` with sudo
        Then I will see the following on stderr:
            """
            To use 'livepatch' you need an Ubuntu Advantage subscription
            Personal and community subscriptions are available at no charge
            See https://ubuntu.com/advantage
            """

        Examples: ua commands
           | enable  |
           | disable |

    @wip
    @series.trusty
    Scenario Outline: Unattached command of an unknown service in a trusty machine
        Given a `trusty` machine with ubuntu-advantage-tools installed
        When I run `ua <command> foobar` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua <command> foobar` with sudo
        Then I will see the following on stderr:
            """
            Cannot <command> '<service>'
            For a list of services see: sudo ua status
            """

        Examples: ua commands
           | command | service     |
           | enable  | livepatch   |
           | disable | foobar foo  |

    @series.trusty
    Scenario: Unattached auto-attach does nothing in a trusty machine
        Given a `trusty` machine with ubuntu-advantage-tools installed
        When I run `ua auto-attach` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua auto-attach` with sudo
        Then stderr matches regexp:
            """
            Auto-attach image support is not available on nocloudnet
            See: https://ubuntu.com/advantage
            """

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
        When I run `ua <command> livepatch` with sudo
        Then stderr matches regexp:
            """
            To use 'livepatch' you need an Ubuntu Advantage subscription
            Personal and community subscriptions are available at no charge
            See https://ubuntu.com/advantage
            """

        Examples: ua commands
           | command |
           | disable |
           | enable  |

    @series.focal
    Scenario Outline: Unattached command of an unknown service in a focal machine
        Given a `focal` machine with ubuntu-advantage-tools installed
        When I run `ua <command> foobar` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua <command> foobar` with sudo
        Then stderr matches regexp:
            """
            Cannot <command> 'foobar'
            For a list of services see: sudo ua status
            """

        Examples: ua commands
           | command |
           | disable |
           | enable  |

    @series.focal
    Scenario: Unattached auto-attach does nothing in a focal machine
        Given a `focal` machine with ubuntu-advantage-tools installed
        When I run `ua auto-attach` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua auto-attach` with sudo
        Then stderr matches regexp:
            """
            Auto-attach image support is not available on lxd
            See: https://ubuntu.com/advantage
            """
