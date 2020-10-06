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
           | bionic  | detach  |
           | bionic  | refresh |
           | focal   | detach  |
           | focal   | refresh |
           | trusty  | detach  |
           | trusty  | refresh |
           | xenial  | detach  |
           | xenial  | refresh |

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
           | bionic  | enable   | livepatch |
           | bionic  | disable  | livepatch |
           | bionic  | enable   | unknown   |
           | bionic  | disable  | unknown   |
           | focal   | enable   | livepatch |
           | focal   | disable  | livepatch |
           | focal   | enable   | unknown   |
           | focal   | disable  | unknown   |
           | trusty  | enable   | livepatch |
           | trusty  | disable  | livepatch |
           | trusty  | enable   | unknown   |
           | trusty  | disable  | unknown   |
           | xenial  | enable   | livepatch |
           | xenial  | disable  | livepatch |
           | xenial  | enable   | unknown   |
           | xenial  | disable  | unknown   |

    @series.all
    Scenario Outline: Help command on an unattached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `ua help esm-infra` as non-root
        Then I will see the following on stdout:
            """
            Name:
            esm-infra

            Available:
            yes

            Help:
            UA Infra: Extended Security Maintenance is enabled by default on entitled
            workloads. It provides access to a private PPA which includes available
            high and critical CVE fixes for Ubuntu LTS packages in the Ubuntu Main
            repository between the end of the standard (free) Ubuntu LTS security
            maintenance and its end of life. You can find out more about the esm
            service at https://ubuntu.com/security/esm.
            """
        When I run `ua help esm-infra --format json` with sudo
        Then I will see the following on stdout:
            """
            {"name": "esm-infra", "available": "yes", "help": "UA Infra: Extended Security Maintenance is enabled by default on entitled\nworkloads. It provides access to a private PPA which includes available\nhigh and critical CVE fixes for Ubuntu LTS packages in the Ubuntu Main\nrepository between the end of the standard (free) Ubuntu LTS security\nmaintenance and its end of life. You can find out more about the esm\nservice at https://ubuntu.com/security/esm.\n"}
            """
        When I run `ua help invalid-service` with sudo
        Then I will see the following on stdout:
            """
            Name:
            invalid-service

            Help:
            No help available for "invalid-service"
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | trusty  |
           | xenial  |
