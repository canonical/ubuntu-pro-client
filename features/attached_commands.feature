@uses.config.contract_token
Feature: Command behaviour when attached to an Ubuntu Pro subscription

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached refresh in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `pro refresh` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\).
            """
        When I run `pro refresh` with sudo
        Then I will see the following on stdout:
            """
            Successfully processed your pro configuration.
            Successfully refreshed your subscription.
            Successfully updated Ubuntu Pro related APT and MOTD messages.
            """
        When I run `pro refresh config` with sudo
        Then I will see the following on stdout:
            """
            Successfully processed your pro configuration.
            """
        When I run `pro refresh contract` with sudo
        Then I will see the following on stdout:
            """
            Successfully refreshed your subscription.
            """
        When I run `pro refresh messages` with sudo
        Then I will see the following on stdout:
            """
            Successfully updated Ubuntu Pro related APT and MOTD messages.
            """
        When I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        And I run `sh -c "ls /var/log/ubuntu-advantage* | sort -d"` as non-root
        Then stdout matches regexp:
        """
        /var/log/ubuntu-advantage.log
        /var/log/ubuntu-advantage-timer.log
        """
        When I run `logrotate --force /etc/logrotate.d/ubuntu-advantage-tools` with sudo
        And I run `sh -c "ls /var/log/ubuntu-advantage* | sort -d"` as non-root
        Then stdout matches regexp:
        """
        /var/log/ubuntu-advantage.log
        /var/log/ubuntu-advantage.log.1
        /var/log/ubuntu-advantage-timer.log
        /var/log/ubuntu-advantage-timer.log.1
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
    Scenario Outline: Attached disable of an already disabled service in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `pro disable livepatch` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\).
            """
        And I verify that running `pro disable livepatch` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            Livepatch is not currently enabled
            See: sudo pro status
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | xenial  |
           | jammy   |
           | kinetic |
           | lunar   |

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached disable with json format
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `pro disable foobar --format json` `as non-root` exits `1`
        And stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
            """
            {"_schema_version": "0.1", "errors": [{"message": "json formatted response requires --assume-yes flag.", "message_code": "json-format-require-assume-yes", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
            """
        Then I verify that running `pro disable foobar --format json` `with sudo` exits `1`
        And stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
            """
            {"_schema_version": "0.1", "errors": [{"message": "json formatted response requires --assume-yes flag.", "message_code": "json-format-require-assume-yes", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
            """
        Then I verify that running `pro disable foobar --format json --assume-yes` `as non-root` exits `1`
        And stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
            """
            {"_schema_version": "0.1", "errors": [{"message": "This command must be run as root (try using sudo).", "message_code": "nonroot-user", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
            """
        And I verify that running `pro disable foobar --format json --assume-yes` `with sudo` exits `1`
        And stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
            """
            {"_schema_version": "0.1", "errors": [{"message": "Cannot disable unknown service 'foobar'.\nTry <valid_services>", "message_code": "invalid-service-or-failure", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
            """
        And I verify that running `pro disable livepatch --format json --assume-yes` `with sudo` exits `1`
        And stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
        """
        {"_schema_version": "0.1", "errors": [{"message": "Livepatch is not currently enabled\nSee: sudo pro status", "message_code": "service-already-disabled", "service": "livepatch", "type": "service"}], "failed_services": ["livepatch"], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
        """
        And I verify that running `pro disable esm-infra esm-apps --format json --assume-yes` `with sudo` exits `0`
        And stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
        """
        {"_schema_version": "0.1", "errors": [], "failed_services": [], "needs_reboot": false, "processed_services": ["esm-apps", "esm-infra"], "result": "success", "warnings": []}
        """
        When I run `pro enable esm-infra` with sudo
        Then I verify that running `pro disable esm-infra foobar --format json --assume-yes` `with sudo` exits `1`
        And stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
        """
        {"_schema_version": "0.1", "errors": [{"message": "Cannot disable unknown service 'foobar'.\nTry <valid_services>", "message_code": "invalid-service-or-failure", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": ["esm-infra"], "result": "failure", "warnings": []}
        """

        Examples: ubuntu release
           | release | valid_services                                                                      |
           | xenial  | cc-eal, cis, esm-apps, esm-infra, fips, fips-updates, livepatch,\nrealtime-kernel, ros, ros-updates. |
           | bionic  | cc-eal, cis, esm-apps, esm-infra, fips, fips-updates, livepatch,\nrealtime-kernel, ros, ros-updates. |
           | focal   | cc-eal, esm-apps, esm-infra, fips, fips-updates, livepatch, realtime-kernel,\nros, ros-updates, usg. |
           | jammy   | cc-eal, esm-apps, esm-infra, fips, fips-updates, livepatch, realtime-kernel,\nros, ros-updates, usg. |

    @series.xenial
    @series.bionic
    @series.jammy
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached disable of a service in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `pro disable foobar` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\).
            """
        And I verify that running `pro disable foobar` `with sudo` exits `1`
        And stderr matches regexp:
            """
            Cannot disable unknown service 'foobar'.
            <msg>
            """
        And I verify that running `pro disable esm-infra` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\).
            """
        When I run `pro disable esm-infra` with sudo
        Then I will see the following on stdout:
            """
            Updating package lists
            """
        When I run `pro status` with sudo
        Then stdout matches regexp:
            """
            esm-infra    +yes      +disabled +Expanded Security Maintenance for Infrastructure
            """
        And I verify that running `apt update` `with sudo` exits `0`

        Examples: ubuntu release
           | release | msg                                                                                                      |
           | xenial  | Try cc-eal, cis, esm-apps, esm-infra, fips, fips-updates, livepatch,\nrealtime-kernel, ros, ros-updates. |
           | bionic  | Try cc-eal, cis, esm-apps, esm-infra, fips, fips-updates, livepatch,\nrealtime-kernel, ros, ros-updates. |
           | jammy   | Try cc-eal, esm-apps, esm-infra, fips, fips-updates, livepatch, realtime-kernel,\nros, ros-updates, usg. |

    @series.focal
    @uses.config.machine_type.lxd.container
    Scenario: Attached disable of a service in a ubuntu machine
        Given a `focal` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `pro disable foobar` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\).
            """
        And I verify that running `pro disable foobar` `with sudo` exits `1`
        And stderr matches regexp:
            """
            Cannot disable unknown service 'foobar'.
            Try cc-eal, esm-apps, esm-infra, fips, fips-updates, livepatch, realtime-kernel,
            ros, ros-updates, usg.
            """
        And I verify that running `pro disable esm-infra` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\).
            """
        When I run `pro disable esm-infra` with sudo
        Then I will see the following on stdout:
            """
            Updating package lists
            """
        When I run `pro status` with sudo
        Then stdout matches regexp:
            """
            esm-infra    +yes      +disabled +Expanded Security Maintenance for Infrastructure
            """
        And I verify that running `apt update` `with sudo` exits `0`


    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached detach in an ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `pro detach` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\).
            """
        When I run `pro detach --assume-yes` with sudo
        Then I will see the following on stdout:
            """
            Detach will disable the following services:
                esm-apps
                esm-infra
            Updating package lists
            Updating package lists
            This machine is now detached.
            """
       When I run `pro status --all` as non-root
       Then stdout matches regexp:
          """
          SERVICE       +AVAILABLE  DESCRIPTION
          cc-eal        +<cc-eal>   +Common Criteria EAL2 Provisioning Packages
          """
       Then stdout matches regexp:
          """
          esm-apps      +<esm-apps> +Expanded Security Maintenance for Applications
          esm-infra     +yes        +Expanded Security Maintenance for Infrastructure
          fips          +<fips>     +NIST-certified core packages
          fips-updates  +<fips>     +NIST-certified core packages with priority security updates
          livepatch     +(yes|no)   +(Canonical Livepatch service|Current kernel is not supported)
          realtime-kernel +<realtime-kernel> +Ubuntu kernel with PREEMPT_RT patches integrated
          ros           +<ros>      +Security Updates for the Robot Operating System
          ros-updates   +<ros>      +All Updates for the Robot Operating System
          """
       Then stdout matches regexp:
          """
          <cis_or_usg>           +<cis>      +Security compliance and audit tools
          """
       And stdout matches regexp:
          """
          This machine is not attached to an Ubuntu Pro subscription.
          """
       And I verify that running `apt update` `with sudo` exits `0`
       When I attach `contract_token` with sudo
       Then I verify that running `pro enable foobar --format json` `as non-root` exits `1`
       And stdout is a json matching the `ua_operation` schema
       And I will see the following on stdout:
           """
           {"_schema_version": "0.1", "errors": [{"message": "json formatted response requires --assume-yes flag.", "message_code": "json-format-require-assume-yes", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
            """
       Then I verify that running `pro enable foobar --format json` `with sudo` exits `1`
       And stdout is a json matching the `ua_operation` schema
       And I will see the following on stdout:
           """
           {"_schema_version": "0.1", "errors": [{"message": "json formatted response requires --assume-yes flag.", "message_code": "json-format-require-assume-yes", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
           """
       Then I verify that running `pro detach --format json --assume-yes` `as non-root` exits `1`
       And stdout is a json matching the `ua_operation` schema
       And I will see the following on stdout:
           """
           {"_schema_version": "0.1", "errors": [{"message": "This command must be run as root (try using sudo).", "message_code": "nonroot-user", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
           """
       When I run `pro detach --format json --assume-yes` with sudo
       Then stdout is a json matching the `ua_operation` schema
       And I will see the following on stdout:
           """
           {"_schema_version": "0.1", "errors": [], "failed_services": [], "needs_reboot": false, "processed_services": ["esm-apps", "esm-infra"], "result": "success", "warnings": []}
           """

       Examples: ubuntu release
           | release | esm-apps | cc-eal | cis | fips | fips-update | ros | cis_or_usg | realtime-kernel |
           | xenial  | yes      | yes    | yes | yes  | yes         | yes | cis        | no              |
           | bionic  | yes      | yes    | yes | yes  | yes         | yes | cis        | no              |
           | focal   | yes      | no     | yes | yes  | yes         | no  | usg        | no              |
           | jammy   | yes      | no     | no  | no   | no          | no  | usg        | yes             |

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached auto-attach in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `pro auto-attach` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\).
            """
        When I verify that running `pro auto-attach` `with sudo` exits `2`
        Then stderr matches regexp:
            """
            This machine is already attached to 'UA Client Test'
            To use a different subscription first run: sudo pro detach.
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
    Scenario Outline: Attached show version in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `pro version` as non-root
        Then I will see the uaclient version on stdout
        When I run `pro version` with sudo
        Then I will see the uaclient version on stdout
        When I run `pro --version` as non-root
        Then I will see the uaclient version on stdout
        When I run `pro --version` with sudo
        Then I will see the uaclient version on stdout

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
    Scenario Outline: Attached status in a ubuntu machine with feature overrides
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I create the file `/tmp/machine-token-overlay.json` with the following:
        """
        {
            "machineTokenInfo": {
                "contractInfo": {
                    "resourceEntitlements": [
                        {
                            "type": "cc-eal",
                            "entitled": false
                        }
                    ]
                }
            }
        }
        """
        And I append the following on uaclient config:
        """
        features:
          machine_token_overlay: "/tmp/machine-token-overlay.json"
          disable_auto_attach: true
          other: false
        """
        And I attach `contract_token` with sudo
        And I run `pro status --all` with sudo
        Then stdout matches regexp:
        """
        SERVICE       +ENTITLED  STATUS    DESCRIPTION
        cc-eal        +no
        """
        And stdout matches regexp:
        """
        FEATURES
        disable_auto_attach: True
        machine_token_overlay: /tmp/machine-token-overlay.json
        other: False
        """
        When I run `pro status --all` as non-root
        Then stdout matches regexp:
        """
        SERVICE       +ENTITLED  STATUS    DESCRIPTION
        cc-eal        +no
        """
        And stdout matches regexp:
        """
        FEATURES
        disable_auto_attach: True
        machine_token_overlay: /tmp/machine-token-overlay.json
        other: False
        """
        When I run `pro detach --assume-yes` with sudo
        Then I verify that running `pro auto-attach` `with sudo` exits `1`
        Then stderr matches regexp:
        """
        features.disable_auto_attach set in config
        """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | xenial  |
           | jammy   |
           | kinetic |
           | lunar   |

    @series.xenial
    @series.bionic
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached disable of different services in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `pro disable esm-infra livepatch foobar` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\)
            """
        And I verify that running `pro disable esm-infra livepatch foobar` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            Updating package lists
            Livepatch is not currently enabled
            See: sudo pro status
            """
        And stderr matches regexp:
            """
            Cannot disable unknown service 'foobar'.
            Try cc-eal, cis, esm-apps, esm-infra, fips, fips-updates, livepatch,
            realtime-kernel, ros, ros-updates.
            """
        When I run `pro status` with sudo
        Then stdout matches regexp:
            """
            esm-infra    +yes      +disabled +Expanded Security Maintenance for Infrastructure
            """
        When I run `touch /var/run/reboot-required` with sudo
        And I run `touch /var/run/reboot-required.pkgs` with sudo
        And I run `pro enable esm-infra` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            Ubuntu Pro: ESM Infra enabled
            """
        And stdout does not match regexp:
            """
            A reboot is required to complete install.
            """

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | jammy   |

    @series.focal
    @uses.config.machine_type.lxd.container
    Scenario: Attached disable of different services in a ubuntu machine
        Given a `focal` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `pro disable esm-infra livepatch foobar` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\)
            """
        And I verify that running `pro disable esm-infra livepatch foobar` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            Updating package lists
            Livepatch is not currently enabled
            See: sudo pro status
            """
        And stderr matches regexp:
            """
            Cannot disable unknown service 'foobar'.
            Try cc-eal, esm-apps, esm-infra, fips, fips-updates, livepatch, realtime-kernel,
            ros, ros-updates, usg.
            """
        When I run `pro status` with sudo
        Then stdout matches regexp:
            """
            esm-infra    +yes      +disabled +Expanded Security Maintenance for Infrastructure
            """
        When I run `touch /var/run/reboot-required` with sudo
        And I run `touch /var/run/reboot-required.pkgs` with sudo
        And I run `pro enable esm-infra` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            Ubuntu Pro: ESM Infra enabled
            """
        And stdout does not match regexp:
            """
            A reboot is required to complete install.
            """

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Help command on an attached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `pro help esm-infra` with sudo
        Then I will see the following on stdout:
        """
        Name:
        esm-infra

        Entitled:
        yes

        Status:
        <infra-status>

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
        {"name": "esm-infra", "entitled": "yes", "status": "<infra-status>", "help": "Expanded Security Maintenance for Infrastructure provides access\nto a private ppa which includes available high and critical CVE fixes\nfor Ubuntu LTS packages in the Ubuntu Main repository between the end\nof the standard Ubuntu LTS security maintenance and its end of life.\nIt is enabled by default with Ubuntu Pro. You can find out more about\nthe service at https://ubuntu.com/security/esm\n"}
        """
        And I verify that running `pro help invalid-service` `with sudo` exits `1`
        And I will see the following on stderr:
        """
        No help available for 'invalid-service'
        """
        When I run `pro --help` as non-root
        Then stdout matches regexp:
        """
        Client to manage Ubuntu Pro services on a machine.
         - cc-eal: Common Criteria EAL2 Provisioning Packages
           \(https://ubuntu.com/cc-eal\)
         - cis: Security compliance and audit tools
           \(https://ubuntu.com/security/certifications/docs/usg\)
         - esm-apps: Expanded Security Maintenance for Applications
           \(https://ubuntu.com/security/esm\)
         - esm-infra: Expanded Security Maintenance for Infrastructure
           \(https://ubuntu.com/security/esm\)
         - fips-updates: NIST-certified core packages with priority security updates
           \(https://ubuntu.com/security/certifications#fips\)
         - fips: NIST-certified core packages
           \(https://ubuntu.com/security/certifications#fips\)
         - livepatch: Canonical Livepatch service
           \(https://ubuntu.com/security/livepatch\)
        """
        When I run `pro help` with sudo
        Then stdout matches regexp:
        """
        Client to manage Ubuntu Pro services on a machine.
         - cc-eal: Common Criteria EAL2 Provisioning Packages
           \(https://ubuntu.com/cc-eal\)
         - cis: Security compliance and audit tools
           \(https://ubuntu.com/security/certifications/docs/usg\)
         - esm-apps: Expanded Security Maintenance for Applications
           \(https://ubuntu.com/security/esm\)
         - esm-infra: Expanded Security Maintenance for Infrastructure
           \(https://ubuntu.com/security/esm\)
         - fips-updates: NIST-certified core packages with priority security updates
           \(https://ubuntu.com/security/certifications#fips\)
         - fips: NIST-certified core packages
           \(https://ubuntu.com/security/certifications#fips\)
         - livepatch: Canonical Livepatch service
           \(https://ubuntu.com/security/livepatch\)
        """
        When I run `pro help --all` as non-root
        Then stdout matches regexp:
        """
        Client to manage Ubuntu Pro services on a machine.
         - cc-eal: Common Criteria EAL2 Provisioning Packages
           \(https://ubuntu.com/cc-eal\)
         - cis: Security compliance and audit tools
           \(https://ubuntu.com/security/certifications/docs/usg\)
         - esm-apps: Expanded Security Maintenance for Applications
           \(https://ubuntu.com/security/esm\)
         - esm-infra: Expanded Security Maintenance for Infrastructure
           \(https://ubuntu.com/security/esm\)
         - fips-updates: NIST-certified core packages with priority security updates
           \(https://ubuntu.com/security/certifications#fips\)
         - fips: NIST-certified core packages
           \(https://ubuntu.com/security/certifications#fips\)
         - livepatch: Canonical Livepatch service
           \(https://ubuntu.com/security/livepatch\)
         - realtime-kernel: Ubuntu kernel with PREEMPT_RT patches integrated
           \(https://ubuntu.com/realtime-kernel\)
         - ros-updates: All Updates for the Robot Operating System
           \(https://ubuntu.com/robotics/ros-esm\)
         - ros: Security Updates for the Robot Operating System
           \(https://ubuntu.com/robotics/ros-esm\)
        """

        Examples: ubuntu release
           | release | infra-status |
           | bionic  | enabled      |
           | xenial  | enabled      |
           | kinetic | n/a          |
           | lunar   | n/a          |

    @series.jammy
    @series.focal
    @uses.config.machine_type.lxd.container
    Scenario Outline: Help command on an attached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `pro help esm-infra` with sudo
        Then I will see the following on stdout:
        """
        Name:
        esm-infra

        Entitled:
        yes

        Status:
        enabled

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
        {"name": "esm-infra", "entitled": "yes", "status": "enabled", "help": "Expanded Security Maintenance for Infrastructure provides access\nto a private ppa which includes available high and critical CVE fixes\nfor Ubuntu LTS packages in the Ubuntu Main repository between the end\nof the standard Ubuntu LTS security maintenance and its end of life.\nIt is enabled by default with Ubuntu Pro. You can find out more about\nthe service at https://ubuntu.com/security/esm\n"}
        """
        And I verify that running `pro help invalid-service` `with sudo` exits `1`
        And I will see the following on stderr:
        """
        No help available for 'invalid-service'
        """
        When I run `pro --help` as non-root
        Then stdout matches regexp:
        """
        Client to manage Ubuntu Pro services on a machine.
         - cc-eal: Common Criteria EAL2 Provisioning Packages
           \(https://ubuntu.com/cc-eal\)
         - esm-apps: Expanded Security Maintenance for Applications
           \(https://ubuntu.com/security/esm\)
         - esm-infra: Expanded Security Maintenance for Infrastructure
           \(https://ubuntu.com/security/esm\)
         - fips-updates: NIST-certified core packages with priority security updates
           \(https://ubuntu.com/security/certifications#fips\)
         - fips: NIST-certified core packages
           \(https://ubuntu.com/security/certifications#fips\)
         - livepatch: Canonical Livepatch service
           \(https://ubuntu.com/security/livepatch\)
         - realtime-kernel: Ubuntu kernel with PREEMPT_RT patches integrated
           \(https://ubuntu.com/realtime-kernel\)
         - ros-updates: All Updates for the Robot Operating System
           \(https://ubuntu.com/robotics/ros-esm\)
         - ros: Security Updates for the Robot Operating System
           \(https://ubuntu.com/robotics/ros-esm\)
         - usg: Security compliance and audit tools
           \(https://ubuntu.com/security/certifications/docs/usg\)
        """
        When I run `pro help` with sudo
        Then stdout matches regexp:
        """
        Client to manage Ubuntu Pro services on a machine.
         - cc-eal: Common Criteria EAL2 Provisioning Packages
           \(https://ubuntu.com/cc-eal\)
         - esm-apps: Expanded Security Maintenance for Applications
           \(https://ubuntu.com/security/esm\)
         - esm-infra: Expanded Security Maintenance for Infrastructure
           \(https://ubuntu.com/security/esm\)
         - fips-updates: NIST-certified core packages with priority security updates
           \(https://ubuntu.com/security/certifications#fips\)
         - fips: NIST-certified core packages
           \(https://ubuntu.com/security/certifications#fips\)
         - livepatch: Canonical Livepatch service
           \(https://ubuntu.com/security/livepatch\)
         - realtime-kernel: Ubuntu kernel with PREEMPT_RT patches integrated
           \(https://ubuntu.com/realtime-kernel\)
         - ros-updates: All Updates for the Robot Operating System
           \(https://ubuntu.com/robotics/ros-esm\)
         - ros: Security Updates for the Robot Operating System
           \(https://ubuntu.com/robotics/ros-esm\)
         - usg: Security compliance and audit tools
           \(https://ubuntu.com/security/certifications/docs/usg\)
        """
        When I run `pro help --all` as non-root
        Then stdout matches regexp:
        """
        Client to manage Ubuntu Pro services on a machine.
         - cc-eal: Common Criteria EAL2 Provisioning Packages
           \(https://ubuntu.com/cc-eal\)
         - esm-apps: Expanded Security Maintenance for Applications
           \(https://ubuntu.com/security/esm\)
         - esm-infra: Expanded Security Maintenance for Infrastructure
           \(https://ubuntu.com/security/esm\)
         - fips-updates: NIST-certified core packages with priority security updates
           \(https://ubuntu.com/security/certifications#fips\)
         - fips: NIST-certified core packages
           \(https://ubuntu.com/security/certifications#fips\)
         - livepatch: Canonical Livepatch service
           \(https://ubuntu.com/security/livepatch\)
         - realtime-kernel: Ubuntu kernel with PREEMPT_RT patches integrated
           \(https://ubuntu.com/realtime-kernel\)
         - ros-updates: All Updates for the Robot Operating System
           \(https://ubuntu.com/robotics/ros-esm\)
         - ros: Security Updates for the Robot Operating System
           \(https://ubuntu.com/robotics/ros-esm\)
         - usg: Security compliance and audit tools
           \(https://ubuntu.com/security/certifications/docs/usg\)
        """

        Examples: ubuntu release
           | release |
           | focal   |
           | jammy   |

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: Enable command with invalid repositories in user machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `pro disable esm-infra` with sudo
        And I run `add-apt-repository ppa:cloud-init-dev/daily -y` with sudo, retrying exit [1]
        And I run `apt update` with sudo
        And I run `sed -i 's/ubuntu/ubun/' /etc/apt/sources.list.d/<ppa_file>.list` with sudo
        And I verify that running `pro enable esm-infra` `with sudo` exits `1`
        Then stdout matches regexp:
        """
        One moment, checking your subscription first
        Updating package lists
        APT update failed.
        APT update failed to read APT config for the following URL:
        - http(s)?://ppa.launchpad(content)?.net/cloud-init-dev/daily/ubun
        """

        Examples: ubuntu release
           | release | ppa_file                           |
           | xenial  | cloud-init-dev-ubuntu-daily-xenial |
           | bionic  | cloud-init-dev-ubuntu-daily-bionic |
           | focal   | cloud-init-dev-ubuntu-daily-focal  |
           | jammy   | cloud-init-dev-ubuntu-daily-jammy  |

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Run timer script on an attached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `systemctl stop ua-timer.timer` with sudo
        And I attach `contract_token` with sudo
        Then I verify that running `pro config set update_messaging_timer=-2` `with sudo` exits `1`
        And stderr matches regexp:
        """
        Cannot set update_messaging_timer to -2: <value> for interval must be a positive integer.
        """
        When I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        And I run `cat /var/lib/ubuntu-advantage/jobs-status.json` with sudo
        Then stdout matches regexp:
        """
        "update_messaging":
        """
        When I run `pro config show` with sudo
        Then stdout matches regexp:
        """
        update_messaging_timer  +21600
        """
        When I delete the file `/var/lib/ubuntu-advantage/jobs-status.json`
        And I run `pro config set update_messaging_timer=0` with sudo
        And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        And I run `cat /var/lib/ubuntu-advantage/jobs-status.json` with sudo
        Then stdout matches regexp:
        """
        "update_messaging": null
        """
        When I delete the file `/var/lib/ubuntu-advantage/jobs-status.json`
        And I create the file `/var/lib/ubuntu-advantage/user-config.json` with the following:
        """
        { "metering_timer": 0 }
        """
        And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        And I run `cat /var/lib/ubuntu-advantage/jobs-status.json` with sudo
        Then stdout matches regexp:
        """
        "metering": null
        """
        When I delete the file `/var/lib/ubuntu-advantage/jobs-status.json`
        And I create the file `/var/lib/ubuntu-advantage/user-config.json` with the following:
        """
        { "metering_timer": "notanumber", "update_messaging_timer": -10 }
        """
        And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        Then I verify that running `grep "Invalid value for update_messaging interval found in config." /var/log/ubuntu-advantage-timer.log` `with sudo` exits `0`
        And I verify that the timer interval for `update_messaging` is `21600`
        And I verify that the timer interval for `metering` is `14400`
        When I create the file `/var/lib/ubuntu-advantage/jobs-status.json` with the following:
        """
        {"metering": {"last_run": "2022-11-29T19:15:52.434906+00:00", "next_run": "2022-11-29T23:15:52.434906+00:00"}, "update_messaging": {"last_run": "2022-11-29T19:15:52.434906+00:00", "next_run": "2022-11-30T01:15:52.434906+00:00"}, "update_status": {"last_run": "2022-11-29T19:15:52.434906+00:00", "next_run": "2022-11-30T01:15:52.434906+00:00"}}
        """
        And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        And I run `cat /var/lib/ubuntu-advantage/jobs-status.json` with sudo
        Then stdout does not match regexp:
        """
        "update_status"
        """
        And stdout matches regexp:
        """
        "metering"
        """
        And stdout matches regexp:
        """
        "update_messaging"
        """

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | jammy   |
           | kinetic |
           | lunar   |

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: Run timer script to valid machine activity endpoint
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `apt install jq -y` with sudo
        And I save the `activityInfo.activityToken` value from the contract
        And I save the `activityInfo.activityID` value from the contract
        # normal metering call when activityId is set by attach response above, expect new
        # token and same id
        And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        Then I verify that `activityInfo.activityToken` value has been updated on the contract
        And I verify that `activityInfo.activityID` value has not been updated on the contract
        When I restore the saved `activityInfo.activityToken` value on contract
        And I delete the file `/var/lib/ubuntu-advantage/jobs-status.json`
        # simulate "cloned" metering call where previously used activityToken is sent again,
        # expect new token and new id
        And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        Then I verify that `activityInfo.activityToken` value has been updated on the contract
        And I verify that `activityInfo.activityID` value has been updated on the contract
        # We are keeping this test to guarantee that the activityPingInterval is also updated
        When I create the file `/tmp/machine-token-overlay.json` with the following:
        """
        {
            "machineTokenInfo": {
                "contractInfo": {
                   "id": "testCID"
                },
                "machineId": "testMID"
            }
        }
        """
        And I create the file `/tmp/response-overlay.json` with the following:
        """
        {
            "https://contracts.canonical.com/v1/contracts/testCID/machine-activity/testMID": [
            {
              "code": 200,
              "response": {
                "activityToken": "test-activity-token",
                "activityID": "test-activity-id",
                "activityPingInterval": 123456789
              }
            }]
        }
        """
        And I append the following on uaclient config:
        """
        features:
          machine_token_overlay: "/tmp/machine-token-overlay.json"
          serviceclient_url_responses: "/tmp/response-overlay.json"
        """
        When I delete the file `/var/lib/ubuntu-advantage/jobs-status.json`
        And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        Then I verify that running `grep -q activityInfo /var/lib/ubuntu-advantage/private/machine-token.json` `with sudo` exits `0`
        And I verify that running `grep -q "\"activityToken\": \"test-activity-token\"" /var/lib/ubuntu-advantage/private/machine-token.json` `with sudo` exits `0`
        And I verify that running `grep -q "\"activityID\": \"test-activity-id\"" /var/lib/ubuntu-advantage/private/machine-token.json` `with sudo` exits `0`
        And I verify that running `grep -q "\"activityPingInterval\": 123456789" /var/lib/ubuntu-advantage/private/machine-token.json` `with sudo` exits `0`
        When I run `cat /var/lib/ubuntu-advantage/jobs-status.json` with sudo
        Then stdout matches regexp:
        """
        \"metering\"
        """

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | jammy   |

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: Run timer script to valid machine activity endpoint
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `rm /var/lib/ubuntu-advantage/machine-token.json` with sudo
        And I run `ua status` as non-root
        Then stdout matches regexp:
        """
        SERVICE +AVAILABLE +DESCRIPTION
        """
        When I run `dpkg-reconfigure ubuntu-advantage-tools` with sudo
        Then I verify that files exist matching `/var/lib/ubuntu-advantage/machine-token.json`
        When I run `ua status` as non-root
        Then stdout matches regexp:
        """
        SERVICE +ENTITLED +STATUS +DESCRIPTION
        """

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | jammy   |
