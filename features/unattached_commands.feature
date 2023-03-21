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
           | lunar   |

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
           | lunar   | detach  |
           | lunar   | refresh |

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
           | lunar    | no              |

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
          | lunar   | enable   |
          | lunar   | disable  |

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
          | lunar   |

    @series.all
    @uses.config.machine_type.lxd.container
    # Side effect: this verifies that `ua` still works as a command
    Scenario Outline: Verify autocomplete options
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I prepare the autocomplete test
        And I press tab twice to autocomplete the `ua` command
        Then stdout matches regexp:
        """
        --debug    +auto-attach   +enable   +status\r
        --help     +collect-logs  +fix      +system\r
        --version  +config        +help     +version\r
        api        +detach        +refresh  +\r
        attach     +disable       +security-status
        """
        When I press tab twice to autocomplete the `pro` command
        Then stdout matches regexp:
        """
        --debug    +auto-attach   +enable   +status\r
        --help     +collect-logs  +fix      +system\r
        --version  +config        +help     +version\r
        api        +detach        +refresh  +\r
        attach     +disable       +security-status
        """
        When I press tab twice to autocomplete the `ua enable` command
        Then stdout matches regexp:
        """
        cc-eal  +esm-infra +livepatch +ros-updates\r
        cis     +fips +realtime-kernel +\r
        esm-apps +fips-updates +ros +\r
        """
        When I press tab twice to autocomplete the `pro enable` command
        Then stdout matches regexp:
        """
        cc-eal  +esm-infra +livepatch +ros-updates\r
        cis     +fips +realtime-kernel +\r
        esm-apps +fips-updates +ros +\r
        """
        When I press tab twice to autocomplete the `ua disable` command
        Then stdout matches regexp:
        """
        cc-eal  +esm-infra +livepatch +ros-updates\r
        cis     +fips +realtime-kernel +\r
        esm-apps +fips-updates +ros +\r
        """
        When I press tab twice to autocomplete the `pro disable` command
        Then stdout matches regexp:
        """
        cc-eal  +esm-infra +livepatch +ros-updates\r
        cis     +fips +realtime-kernel +\r
        esm-apps +fips-updates +ros +\r
        """

        Examples: ubuntu release
          | release |
          # | xenial  | Can't rely on Xenial because of bash sorting things weirdly
          | bionic  |
          | focal   |
          | jammy   |
          # | kinetic | There is a very weird error on Kinetic, irrelevant to this test
          | lunar   |

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: esm cache failures don't generate errors
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I disable access to esm.ubuntu.com
        And I run `apt update` with sudo
        # Wait for the hook to fail
        When I wait `5` seconds
        And I run `systemctl --failed` with sudo
        Then stdout does not match regexp:
        """
        esm-cache\.service
        """
        When I run `journalctl -o cat -u esm-cache.service` with sudo
        Then stdout does not match regexp:
        """
        raise FetchFailedException\(\)
        """
        When I run `ls /var/crash/` with sudo
        Then stdout does not match regexp:
        """
        _usr_lib_ubuntu-advantage_esm_cache
        """
        When I run `cat /var/log/ubuntu-advantage.log` with sudo
        Then stdout matches regexp:
        """
        Failed to fetch the ESM Apt Cache
        """

        Examples: ubuntu release
          | release |
          | xenial  |
          | bionic  |
          | focal   |
          | jammy   |

    @series.jammy
    @series.kinetic
    @series.lunar
    @uses.config.machine_type.lxd.container
    # Services fail, degraded systemctl, but no crashes.
    Scenario Outline: services fail gracefully when yaml is broken/absent
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt update` with sudo
        And I run `rm -rf /usr/lib/python3/dist-packages/yaml` with sudo
        And I verify that running `pro status` `with sudo` exits `1`
        Then stderr matches regexp:
        """
        Couldn't import the YAML module.
        Make sure the 'python3-yaml' package is installed correctly
        and \/usr\/lib\/python3\/dist-packages is in yout PYTHONPATH\.
        """
        When I verify that running `python3 /usr/lib/ubuntu-advantage/esm_cache.py` `with sudo` exits `1`
        Then stderr matches regexp:
        """
        Couldn't import the YAML module.
        Make sure the 'python3-yaml' package is installed correctly
        and \/usr\/lib\/python3\/dist-packages is in yout PYTHONPATH\.
        """
        When I verify that running `systemctl start apt-news.service` `with sudo` exits `1`
        And I verify that running `systemctl start esm-cache.service` `with sudo` exits `1`
        And I run `systemctl --failed` with sudo
        Then stdout matches regexp:
        """
        apt-news.service
        """
        And stdout matches regexp:
        """
        esm-cache.service
        """
        When I run `apt install python3-pip -y` with sudo
        And I run `pip3 install pyyaml==3.10 <suffix>` with sudo
        And I run `ls /usr/local/lib/<python_version>/dist-packages/` with sudo
        Then stdout matches regexp:
        """
        yaml
        """
        And I verify that running `pro status` `with sudo` exits `1`
        Then stderr matches regexp:
        """
        Error while trying to parse a yaml file using 'yaml' from
        """
        # Test the specific script which triggered LP #2007241
        When I verify that running `python3 /usr/lib/ubuntu-advantage/esm_cache.py` `with sudo` exits `1`
        Then stderr matches regexp:
        """
        Error while trying to parse a yaml file using 'yaml' from
        """
        When I verify that running `systemctl start apt-news.service` `with sudo` exits `1`
        And I verify that running `systemctl start esm-cache.service` `with sudo` exits `1`
        And I run `systemctl --failed` with sudo
        Then stdout matches regexp:
        """
        apt-news.service
        """
        And stdout matches regexp:
        """
        esm-cache.service
        """
        When I run `ls /var/crash` with sudo
        Then I will see the following on stdout
        """
        """

        Examples: ubuntu release
          | release | python_version | suffix                  |
          | jammy   | python3.10     |                         |
          | kinetic | python3.10     |                         |
          # Lunar has a BIG error message explaining why this is a clear user error...
          | lunar   | python3.11     | --break-system-packages |
