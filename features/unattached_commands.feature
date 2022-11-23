Feature: Command behaviour when unattached

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Unattached auto-attach does nothing in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        # Validate systemd unit/timer syntax
        When I run `systemd-analyze verify /lib/systemd/system/ua-timer.timer` with sudo
        Then stderr does not match regexp:
            """
            .*\/lib\/systemd/system\/ua.*
            """
        When I verify that running `pro auto-attach` `as non-root` exits `1`
        Then stderr matches regexp:
            """
            This command must be run as root \(try using sudo\).
            """
        When I run `pro auto-attach` with sudo
        Then stderr matches regexp:
            """
            Auto-attach image support is not available on lxd
            See: https://ubuntu.com/pro
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | xenial  |
           | jammy   |
           | kinetic |

    @series.xenial
    @uses.config.machine_type.lxd.container
    Scenario Outline: Disabled unattached APT policy apt-hook for infra and apps
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt update` with sudo
        When I run `apt-cache policy` with sudo
        Then stdout matches regexp:
        """
        -32768 <esm-infra-url> <release>-infra-updates/main amd64 Packages
        """
        And stdout does not match regexp:
        """
        -32768 <esm-apps-url> <release>-apps-updates/main amd64 Packages
        """
        And stdout does not match regexp:
        """
        -32768 <esm-apps-url> <release>-apps-security/main amd64 Packages
        """
        When I append the following on uaclient config:
            """
            features:
              allow_beta: true
            """
        And I run `dpkg-reconfigure ubuntu-advantage-tools` with sudo
        And I run `apt-get update` with sudo
        When I run `apt-cache policy` with sudo
        Then stdout matches regexp:
        """
        -32768 <esm-apps-url> <release>-apps-updates/main amd64 Packages
        """
        And stdout matches regexp:
        """
        -32768 <esm-apps-url> <release>-apps-security/main amd64 Packages
        """
        When I create the file `/etc/apt/sources.list.d/empty-release-origin.list` with the following
        """
        deb [ allow-insecure=yes ] https://packages.irods.org/apt xenial main
        """
        Then I verify that running `apt-get update` `with sudo` exits `0`
        When I delete the file `/var/lib/ubuntu-advantage/jobs-status.json`
        And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        Then I verify that running `/usr/lib/ubuntu-advantage/apt-esm-hook` `with sudo` exits `0`

        Examples: ubuntu release
           | release | esm-infra-url                       | esm-apps-url |
           | xenial  | https://esm.ubuntu.com/infra/ubuntu | https://esm.ubuntu.com/apps/ubuntu |

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Unattached commands that requires enabled user in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I verify that running `pro <command>` `as non-root` exits `1`
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo).
            """
        When I verify that running `pro <command>` `with sudo` exits `1`
        Then stderr matches regexp:
            """
            This machine is not attached to an Ubuntu Pro subscription.
            See https://ubuntu.com/pro
            """

        Examples: pro commands
           | release | command |
           | bionic  | detach  |
           | bionic  | refresh |
           | focal   | detach  |
           | focal   | refresh |
           | xenial  | detach  |
           | xenial  | refresh |
           | kinetic | detach  |
           | kinetic | refresh |
           | jammy   | detach  |
           | jammy   | refresh |

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Help command on an unattached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `pro help esm-infra` as non-root
        Then I will see the following on stdout:
        """
        Name:
        esm-infra

        Available:
        <infra-available>

        Help:
        Expanded Security Maintenance for Infrastructure provides access
        to a private ppa which includes available high and critical CVE fixes
        for Ubuntu LTS packages in the Ubuntu Main repository between the end
        of the standard Ubuntu LTS security maintenance and its end of life.
        It is enabled by default with Ubuntu Pro. You can find out more about
        the service at https://ubuntu.com/security/esm
        """
        When I run `pro help esm-infra --format json` with sudo
        Then I will see the following on stdout:
        """
        {"name": "esm-infra", "available": "<infra-available>", "help": "Expanded Security Maintenance for Infrastructure provides access\nto a private ppa which includes available high and critical CVE fixes\nfor Ubuntu LTS packages in the Ubuntu Main repository between the end\nof the standard Ubuntu LTS security maintenance and its end of life.\nIt is enabled by default with Ubuntu Pro. You can find out more about\nthe service at https://ubuntu.com/security/esm\n"}
        """
        When I verify that running `pro help invalid-service` `with sudo` exits `1`
        Then I will see the following on stderr:
        """
        No help available for 'invalid-service'
        """
        When I verify that running `pro --wrong-flag` `with sudo` exits `2`
        Then I will see the following on stderr:
        """
        usage: pro <command> [flags]
        Try 'pro --help' for more information.
        """

        Examples: ubuntu release
           | release  | infra-available |
           | xenial   | yes             |
           | bionic   | yes             |
           | focal    | yes             |
           | jammy    | yes             |
           | kinetic  | no              |

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Unattached enable/disable fails in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I verify that running `pro <command> esm-infra` `as non-root` exits `1`
        Then I will see the following on stderr:
          """
          This command must be run as root (try using sudo).
          """
        When I verify that running `pro <command> esm-infra` `with sudo` exits `1`
        Then I will see the following on stderr:
          """
          To use 'esm-infra' you need an Ubuntu Pro subscription
          Personal and community subscriptions are available at no charge
          See https://ubuntu.com/pro
          """
        When I verify that running `pro <command> esm-infra --format json --assume-yes` `with sudo` exits `1`
        Then stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
          """
          {"_schema_version": "0.1", "errors": [{"message": "To use 'esm-infra' you need an Ubuntu Pro subscription\nPersonal and community subscriptions are available at no charge\nSee https://ubuntu.com/pro", "message_code": "valid-service-failure-unattached", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
          """
        When I verify that running `pro <command> unknown` `as non-root` exits `1`
        Then I will see the following on stderr:
          """
          This command must be run as root (try using sudo).
          """
        When I verify that running `pro <command> unknown` `with sudo` exits `1`
        Then I will see the following on stderr:
          """
          Cannot <command> unknown service 'unknown'.
          See https://ubuntu.com/pro
          """
        When I verify that running `pro <command> unknown --format json --assume-yes` `with sudo` exits `1`
        Then stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
          """
          {"_schema_version": "0.1", "errors": [{"message": "Cannot <command> unknown service 'unknown'.\nSee https://ubuntu.com/pro", "message_code": "invalid-service-or-failure", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
          """
        When I verify that running `pro <command> esm-infra unknown` `as non-root` exits `1`
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo).
            """
        When I verify that running `pro <command> esm-infra unknown` `with sudo` exits `1`
        Then I will see the following on stderr:
          """
          Cannot <command> unknown service 'unknown'.

          To use 'esm-infra' you need an Ubuntu Pro subscription
          Personal and community subscriptions are available at no charge
          See https://ubuntu.com/pro
          """
        When I verify that running `pro <command> esm-infra unknown --format json --assume-yes` `with sudo` exits `1`
        Then stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
          """
          {"_schema_version": "0.1", "errors": [{"message": "Cannot <command> unknown service 'unknown'.\n\nTo use 'esm-infra' you need an Ubuntu Pro subscription\nPersonal and community subscriptions are available at no charge\nSee https://ubuntu.com/pro", "message_code": "mixed-services-failure-unattached", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
          """

        Examples: ubuntu release
          | release | command  |
          | xenial  | enable   |
          | xenial  | disable  |
          | bionic  | enable   |
          | bionic  | disable  |
          | focal   | enable   |
          | focal   | disable  |
          | kinetic | enable   |
          | kinetic | disable  |
          | jammy   | enable   |
          | jammy   | disable  |

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Check for newer versions of the client in an ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        #  Make sure we have a fresh, just rebooted, environment
        When I reboot the machine
        Then I verify that no files exist matching `/run/ubuntu-advantage/candidate-version`
        When I run `pro status` with sudo
        Then I will see the following on stderr
        """
        """
        And I verify that files exist matching `/run/ubuntu-advantage/candidate-version`
        # We forge a candidate to see results
        When I delete the file `/run/ubuntu-advantage/candidate-version`
        And I create the file `/run/ubuntu-advantage/candidate-version` with the following
        """
        99.9.9
        """
        And I run `pro status` as non-root
        Then stderr matches regexp:
        """
        .*\[info\].* A new version is available: 99.9.9
        Please run:
            sudo apt-get install ubuntu-advantage-tools
        to get the latest version with new features and bug fixes.
        """
        When I run `pro status --format json` as non-root
        Then I will see the following on stderr
        """
        """
        When I run `pro config show` as non-root
        Then stderr matches regexp:
        """
        .*\[info\].* A new version is available: 99.9.9
        Please run:
            sudo apt-get install ubuntu-advantage-tools
        to get the latest version with new features and bug fixes.
        """
        When I run `pro api u.pro.version.v1` as non-root
        Then stdout matches regexp
        """
        \"code\": \"new-version-available\"
        """
        When I verify that running `pro api u.pro.version.inexistent` `as non-root` exits `1`
        Then stdout matches regexp
        """
        \"code\": \"new-version-available\"
        """
        When I run `pro api u.pro.version.v1` as non-root
        Then I will see the following on stderr
        """
        """
        When I run `apt-get update` with sudo
        # apt-get update will bring a new candidate, which is the current installed version
        And I run `pro status` as non-root
        Then I will see the following on stderr
        """
        """

        Examples: ubuntu release
          | release |
          | xenial  |
          | bionic  |
          | focal   |
          | jammy   |
          | kinetic |
