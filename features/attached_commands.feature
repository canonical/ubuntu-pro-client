@uses.config.contract_token
Feature: Command behaviour when attached to an Ubuntu Pro subscription

    Scenario Outline: Attached refresh in a ubuntu machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I verify that `Bearer ` field is redacted in the logs
        And I verify that `'attach', '` field is redacted in the logs
        And I verify that `'machineToken': '` field is redacted in the logs
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
        """
        When I run `logrotate --force /etc/logrotate.d/ubuntu-pro-client` with sudo
        And I run `sh -c "ls /var/log/ubuntu-advantage* | sort -d"` as non-root
        Then stdout matches regexp:
        """
        /var/log/ubuntu-advantage.log
        /var/log/ubuntu-advantage.log.1
        """

        Examples: ubuntu release
           | release | machine_type  |
           | bionic  | lxd-container |
           | focal   | lxd-container |
           | xenial  | lxd-container |
           | jammy   | lxd-container |
           | mantic  | lxd-container |

    Scenario Outline: Disable command on an attached machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `pro disable livepatch` `as non-root` exits `1`
        And stderr matches regexp:
        """
        This command must be run as root \(try using sudo\).
        """
        When I verify that running `pro disable foobar` `as non-root` exits `1`
        Then stderr matches regexp:
        """
        This command must be run as root \(try using sudo\).
        """
        When I verify that running `pro disable livepatch` `with sudo` exits `1`
        Then I will see the following on stdout:
        """
        Livepatch is not currently enabled
        See: sudo pro status
        """
        When I verify that running `pro disable foobar` `with sudo` exits `1`
        Then stderr matches regexp:
        """
        Cannot disable unknown service 'foobar'.
        <msg>
        """
        When I verify that running `pro disable livepatch foobar` `as non-root` exits `1`
        Then stderr matches regexp:
        """
        This command must be run as root \(try using sudo\)
        """
        When I verify that running `pro disable livepatch foobar` `with sudo` exits `1`
        Then I will see the following on stdout:
        """
        Livepatch is not currently enabled
        See: sudo pro status
        """
        And stderr matches regexp:
        """
        Cannot disable unknown service 'foobar'.
        <msg>
        """
        When I verify that running `pro disable esm-infra` `as non-root` exits `1`
        Then stderr matches regexp:
        """
        This command must be run as root \(try using sudo\).
        """
        When I run `pro disable esm-infra` with sudo
        Then I verify that `esm-infra` is disabled
        And I verify that running `apt update` `with sudo` exits `0`

        Examples: ubuntu release
           | release | machine_type  | msg                                                                                                                                            |
           | xenial  | lxd-container | Try anbox-cloud, cc-eal, cis, esm-apps, esm-infra, fips, fips-preview,\nfips-updates, landscape, livepatch, realtime-kernel, ros, ros-updates. |
           | bionic  | lxd-container | Try anbox-cloud, cc-eal, cis, esm-apps, esm-infra, fips, fips-preview,\nfips-updates, landscape, livepatch, realtime-kernel, ros, ros-updates. |
           | focal   | lxd-container | Try anbox-cloud, cc-eal, esm-apps, esm-infra, fips, fips-preview, fips-updates,\nlandscape, livepatch, realtime-kernel, ros, ros-updates, usg. |
           | jammy   | lxd-container | Try anbox-cloud, cc-eal, esm-apps, esm-infra, fips, fips-preview, fips-updates,\nlandscape, livepatch, realtime-kernel, ros, ros-updates, usg. |

    Scenario Outline: Attached disable with json format
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
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
        {"_schema_version": "0.1", "errors": [{"additional_info": {"invalid_service": "foobar", "operation": "disable", "service_msg": "Try <valid_services>"}, "message": "Cannot disable unknown service 'foobar'.\nTry <valid_services>", "message_code": "invalid-service-or-failure", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
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
        {"_schema_version": "0.1", "errors": [{"additional_info": {"invalid_service": "foobar", "operation": "disable", "service_msg": "Try <valid_services>"}, "message": "Cannot disable unknown service 'foobar'.\nTry <valid_services>", "message_code": "invalid-service-or-failure", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": ["esm-infra"], "result": "failure", "warnings": []}
        """

        Examples: ubuntu release
           | release | machine_type  | valid_services                                                                                                                             |
           | xenial  | lxd-container | anbox-cloud, cc-eal, cis, esm-apps, esm-infra, fips, fips-preview,\nfips-updates, landscape, livepatch, realtime-kernel, ros, ros-updates. |
           | bionic  | lxd-container | anbox-cloud, cc-eal, cis, esm-apps, esm-infra, fips, fips-preview,\nfips-updates, landscape, livepatch, realtime-kernel, ros, ros-updates. |
           | focal   | lxd-container | anbox-cloud, cc-eal, esm-apps, esm-infra, fips, fips-preview, fips-updates,\nlandscape, livepatch, realtime-kernel, ros, ros-updates, usg. |
           | jammy   | lxd-container | anbox-cloud, cc-eal, esm-apps, esm-infra, fips, fips-preview, fips-updates,\nlandscape, livepatch, realtime-kernel, ros, ros-updates, usg. |

    Scenario Outline: Attached detach in an ubuntu machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I verify that `Bearer ` field is redacted in the logs
        And I verify that `'attach', '` field is redacted in the logs
        And I verify that `'machineToken': '` field is redacted in the logs
        And I run `pro api u.pro.status.enabled_services.v1` as non-root
        Then stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"enabled_services": \[{"name": "esm-apps", "variant_enabled": false, "variant_name": null}, {"name": "esm-infra", "variant_enabled": false, "variant_name": null}\]}, "meta": {"environment_vars": \[\]}, "type": "EnabledServices"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
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
        And the machine is unattached
        And I ensure apt update runs without errors
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
        And the machine is unattached

       Examples: ubuntu release
           | release | machine_type  |
           | xenial  | lxd-container |
           | bionic  | lxd-container |
           | focal   | lxd-container |
           | jammy   | lxd-container |

    Scenario Outline: Attached auto-attach in a ubuntu machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `pro auto-attach` `as non-root` exits `1`
        And stderr matches regexp:
        """
        This command must be run as root \(try using sudo\).
        """
        When I verify that running `pro auto-attach` `with sudo` exits `2`
        Then stderr matches regexp:
        """
        This machine is already attached to '.+'
        To use a different subscription first run: sudo pro detach.
        """

        Examples: ubuntu release
           | release | machine_type  |
           | bionic  | lxd-container |
           | focal   | lxd-container |
           | xenial  | lxd-container |
           | jammy   | lxd-container |
           | mantic  | lxd-container |

    Scenario Outline: Attached show version in a ubuntu machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
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
           | release | machine_type  |
           | bionic  | lxd-container |
           | focal   | lxd-container |
           | xenial  | lxd-container |
           | jammy   | lxd-container |
           | mantic  | lxd-container |

    Scenario Outline: Attached status in a ubuntu machine with feature overrides
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I create the file `/var/lib/ubuntu-advantage/machine-token-overlay.json` with the following:
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
          machine_token_overlay: "/var/lib/ubuntu-advantage/machine-token-overlay.json"
          disable_auto_attach: true
          other: false
        """
        And I attach `contract_token` with sudo
        And I run `pro status --all` with sudo
        Then stdout matches regexp:
        """
        SERVICE       +ENTITLED +STATUS +DESCRIPTION
        anbox-cloud   +.*
        cc-eal        +no
        """
        And stdout matches regexp:
        """
        FEATURES
        disable_auto_attach: True
        machine_token_overlay: /var/lib/ubuntu-advantage/machine-token-overlay.json
        other: False
        """
        When I run `pro status --all` as non-root
        Then stdout matches regexp:
        """
        SERVICE       +ENTITLED +STATUS +DESCRIPTION
        anbox-cloud   +.*
        cc-eal        +no
        """
        And stdout matches regexp:
        """
        FEATURES
        disable_auto_attach: True
        machine_token_overlay: /var/lib/ubuntu-advantage/machine-token-overlay.json
        other: False
        """
        When I run `pro detach --assume-yes` with sudo
        Then I verify that running `pro auto-attach` `with sudo` exits `1`
        Then stderr matches regexp:
        """
        features.disable_auto_attach set in config
        """

        Examples: ubuntu release
           | release | machine_type  |
           | bionic  | lxd-container |
           | focal   | lxd-container |
           | xenial  | lxd-container |
           | jammy   | lxd-container |
           | mantic  | lxd-container |

    Scenario Outline: Attached enable when reboot required
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `pro disable esm-infra` with sudo
        And I run `touch /var/run/reboot-required` with sudo
        And I run `touch /var/run/reboot-required.pkgs` with sudo
        And I run `pro enable esm-infra` with sudo
        Then stdout matches regexp:
        """
        Updating Ubuntu Pro: ESM Infra package lists
        Ubuntu Pro: ESM Infra enabled
        """
        And stdout does not match regexp:
        """
        A reboot is required to complete install.
        """

        Examples: ubuntu release
           | release | machine_type  |
           | xenial  | lxd-container |
           | bionic  | lxd-container |
           | focal   | lxd-container |
           | jammy   | lxd-container |

    Scenario Outline: Help command on an attached machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
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
        Expanded Security Maintenance for Infrastructure provides access to a private
        PPA which includes available high and critical CVE fixes for Ubuntu LTS
        packages in the Ubuntu Main repository between the end of the standard Ubuntu
        LTS security maintenance and its end of life. It is enabled by default with
        Ubuntu Pro. You can find out more about the service at
        https://ubuntu.com/security/esm
        """
        When I run `pro help esm-infra --format json` with sudo
        Then I will see the following on stdout:
        """
        {"name": "esm-infra", "entitled": "yes", "status": "<infra-status>", "help": "Expanded Security Maintenance for Infrastructure provides access to a private\nPPA which includes available high and critical CVE fixes for Ubuntu LTS\npackages in the Ubuntu Main repository between the end of the standard Ubuntu\nLTS security maintenance and its end of life. It is enabled by default with\nUbuntu Pro. You can find out more about the service at\nhttps://ubuntu.com/security/esm"}
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
         - anbox-cloud: .*
         - cc-eal: Common Criteria EAL2 Provisioning Packages
           \(https://ubuntu.com/security/cc\)
         - cis: Security compliance and audit tools
           \(https://ubuntu.com/security/certifications/docs/usg\)
         - esm-apps: Expanded Security Maintenance for Applications
           \(https://ubuntu.com/security/esm\)
         - esm-infra: Expanded Security Maintenance for Infrastructure
           \(https://ubuntu.com/security/esm\)
         - fips-preview: .*
           .*\(https://ubuntu.com/security/fips\)
         - fips-updates: FIPS compliant crypto packages with stable security updates
           \(https://ubuntu.com/security/fips\)
         - fips: NIST-certified FIPS crypto packages \(https://ubuntu.com/security/fips\)
         - landscape: Management and administration tool for Ubuntu
           \(https://ubuntu.com/landscape\)
         - livepatch: Canonical Livepatch service
           \(https://ubuntu.com/security/livepatch\)
        """
        When I run `pro help` with sudo
        Then stdout matches regexp:
        """
        Client to manage Ubuntu Pro services on a machine.
         - anbox-cloud: .*
         - cc-eal: Common Criteria EAL2 Provisioning Packages
           \(https://ubuntu.com/security/cc\)
         - cis: Security compliance and audit tools
           \(https://ubuntu.com/security/certifications/docs/usg\)
         - esm-apps: Expanded Security Maintenance for Applications
           \(https://ubuntu.com/security/esm\)
         - esm-infra: Expanded Security Maintenance for Infrastructure
           \(https://ubuntu.com/security/esm\)
         - fips-preview: .*
           .*\(https://ubuntu.com/security/fips\)
         - fips-updates: FIPS compliant crypto packages with stable security updates
           \(https://ubuntu.com/security/fips\)
         - fips: NIST-certified FIPS crypto packages \(https://ubuntu.com/security/fips\)
         - landscape: Management and administration tool for Ubuntu
           \(https://ubuntu.com/landscape\)
         - livepatch: Canonical Livepatch service
           \(https://ubuntu.com/security/livepatch\)
        """
        When I run `pro help --all` as non-root
        Then stdout matches regexp:
        """
        Client to manage Ubuntu Pro services on a machine.
         - anbox-cloud: .*
         - cc-eal: Common Criteria EAL2 Provisioning Packages
           \(https://ubuntu.com/security/cc\)
         - cis: Security compliance and audit tools
           \(https://ubuntu.com/security/certifications/docs/usg\)
         - esm-apps: Expanded Security Maintenance for Applications
           \(https://ubuntu.com/security/esm\)
         - esm-infra: Expanded Security Maintenance for Infrastructure
           \(https://ubuntu.com/security/esm\)
         - fips-preview: .*
           .*\(https://ubuntu.com/security/fips\)
         - fips-updates: FIPS compliant crypto packages with stable security updates
           \(https://ubuntu.com/security/fips\)
         - fips: NIST-certified FIPS crypto packages \(https://ubuntu.com/security/fips\)
         - landscape: Management and administration tool for Ubuntu
           \(https://ubuntu.com/landscape\)
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
           | release | machine_type  | infra-status |
           | bionic  | lxd-container | enabled      |
           | xenial  | lxd-container | enabled      |
           | mantic  | lxd-container | n/a          |

    Scenario Outline: Help command on an attached machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
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
        Expanded Security Maintenance for Infrastructure provides access to a private
        PPA which includes available high and critical CVE fixes for Ubuntu LTS
        packages in the Ubuntu Main repository between the end of the standard Ubuntu
        LTS security maintenance and its end of life. It is enabled by default with
        Ubuntu Pro. You can find out more about the service at
        https://ubuntu.com/security/esm
        """
        When I run `pro help esm-infra --format json` with sudo
        Then I will see the following on stdout:
        """
        {"name": "esm-infra", "entitled": "yes", "status": "enabled", "help": "Expanded Security Maintenance for Infrastructure provides access to a private\nPPA which includes available high and critical CVE fixes for Ubuntu LTS\npackages in the Ubuntu Main repository between the end of the standard Ubuntu\nLTS security maintenance and its end of life. It is enabled by default with\nUbuntu Pro. You can find out more about the service at\nhttps://ubuntu.com/security/esm"}
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
         - anbox-cloud: .*
         - cc-eal: Common Criteria EAL2 Provisioning Packages
           \(https://ubuntu.com/security/cc\)
         - esm-apps: Expanded Security Maintenance for Applications
           \(https://ubuntu.com/security/esm\)
         - esm-infra: Expanded Security Maintenance for Infrastructure
           \(https://ubuntu.com/security/esm\)
         - fips-preview: .*
           .*\(https://ubuntu.com/security/fips\)
         - fips-updates: FIPS compliant crypto packages with stable security updates
           \(https://ubuntu.com/security/fips\)
         - fips: NIST-certified FIPS crypto packages \(https://ubuntu.com/security/fips\)
         - landscape: Management and administration tool for Ubuntu
           \(https://ubuntu.com/landscape\)
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
         - anbox-cloud: .*
         - cc-eal: Common Criteria EAL2 Provisioning Packages
           \(https://ubuntu.com/security/cc\)
         - esm-apps: Expanded Security Maintenance for Applications
           \(https://ubuntu.com/security/esm\)
         - esm-infra: Expanded Security Maintenance for Infrastructure
           \(https://ubuntu.com/security/esm\)
         - fips-preview: .*
           .*\(https://ubuntu.com/security/fips\)
         - fips-updates: FIPS compliant crypto packages with stable security updates
           \(https://ubuntu.com/security/fips\)
         - fips: NIST-certified FIPS crypto packages \(https://ubuntu.com/security/fips\)
         - landscape: Management and administration tool for Ubuntu
           \(https://ubuntu.com/landscape\)
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
         - anbox-cloud: .*
         - cc-eal: Common Criteria EAL2 Provisioning Packages
           \(https://ubuntu.com/security/cc\)
         - esm-apps: Expanded Security Maintenance for Applications
           \(https://ubuntu.com/security/esm\)
         - esm-infra: Expanded Security Maintenance for Infrastructure
           \(https://ubuntu.com/security/esm\)
         - fips-preview: .*
           .*\(https://ubuntu.com/security/fips\)
         - fips-updates: FIPS compliant crypto packages with stable security updates
           \(https://ubuntu.com/security/fips\)
         - fips: NIST-certified FIPS crypto packages \(https://ubuntu.com/security/fips\)
         - landscape: Management and administration tool for Ubuntu
           \(https://ubuntu.com/landscape\)
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
           | release | machine_type  |
           | focal   | lxd-container |
           | jammy   | lxd-container |

    Scenario Outline: Run timer script on an attached machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
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
        And I run `systemctl start ua-timer.service` with sudo
        Then I verify that running `sh -c 'journalctl -u ua-timer.service | grep "Invalid value for update_messaging interval found in config."'` `with sudo` exits `0`
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
           | release | machine_type  |
           | xenial  | lxd-container |
           | bionic  | lxd-container |
           | focal   | lxd-container |
           | jammy   | lxd-container |
           | mantic  | lxd-container |

    Scenario Outline: Run timer script to valid machine activity endpoint
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I apt update
        And I apt install `jq`
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
        When I create the file `/var/lib/ubuntu-advantage/machine-token-overlay.json` with the following:
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
        And I create the file `/var/lib/ubuntu-advantage/response-overlay.json` with the following:
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
          machine_token_overlay: "/var/lib/ubuntu-advantage/machine-token-overlay.json"
          serviceclient_url_responses: "/var/lib/ubuntu-advantage/response-overlay.json"
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
           | release | machine_type  |
           | xenial  | lxd-container |
           | bionic  | lxd-container |
           | focal   | lxd-container |
           | jammy   | lxd-container |

    Scenario Outline: Run timer script to valid machine activity endpoint
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `rm /var/lib/ubuntu-advantage/machine-token.json` with sudo
        Then the machine is unattached
        When I run `dpkg-reconfigure ubuntu-advantage-tools` with sudo
        Then I verify that files exist matching `/var/lib/ubuntu-advantage/machine-token.json`
        Then the machine is attached

        Examples: ubuntu release
           | release | machine_type  |
           | xenial  | lxd-container |
           | bionic  | lxd-container |
           | focal   | lxd-container |
           | jammy   | lxd-container |

    Scenario Outline: Disable with purge does not work with assume-yes
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I verify that running `pro disable esm-apps --assume-yes --purge` `with sudo` exits `1`
        Then stderr contains substring:
        """
        Error: Cannot use --purge together with --assume-yes.
        """
        Examples: ubuntu release
           | release | machine_type  |
           | xenial  | lxd-container |
           | bionic  | lxd-container |
           | focal   | lxd-container |
           | jammy   | lxd-container |

    Scenario Outline: Disable with purge works and purges repo services not involving a kernel
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I apt update
        And I apt install `ansible`
        And I run `pro disable esm-apps --purge` `with sudo` and stdin `y`
        Then stdout matches regexp:
        """
        \(The --purge flag is still experimental - use with caution\)

        The following package\(s\) will be reinstalled from the archive:
        .*ansible.*

        Do you want to proceed\? \(y/N\)
        """
        And I verify that `esm-apps` is disabled
        And I verify that `ansible` is installed from apt source `http://archive.ubuntu.com/ubuntu <pocket>/universe`

        Examples: ubuntu release
           | release | machine_type  | pocket           |
           # This ends up in GH #943 but maybe can be improved?
           | xenial  | lxd-container | xenial-backports |
           | bionic  | lxd-container | bionic-updates   |
           | focal   | lxd-container | focal            |
           | jammy   | lxd-container | jammy            |

    Scenario Outline: Disable with purge unsupported services
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I verify that running `pro disable livepatch --purge` `with sudo` exits `1`
        Then I will see the following on stdout:
        """
        Livepatch does not support being disabled with --purge
        """

        Examples: ubuntu release
           | release | machine_type |
           | xenial  | lxd-vm       |
           | bionic  | lxd-vm       |
           | focal   | lxd-vm       |
           | jammy   | lxd-vm       |

    @slow
    Scenario Outline: Disable and purge fips
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I apt update
        And I run `pro enable <fips-service> --assume-yes` with sudo
        And I reboot the machine
        Then I verify that `<fips-service>` is enabled
        When  I run `uname -r` as non-root
        Then stdout matches regexp:
        """
        fips
        """
        And I verify that `openssh-server` is installed from apt source `<fips-source>`
        And I verify that `<kernel-package>` is installed from apt source `<fips-source>`
        When I run `pro disable <fips-service> --purge` `with sudo` and stdin `y\ny`
        Then stdout matches regexp:
        """
        \(The --purge flag is still experimental - use with caution\)

        Purging the <fips-name> packages would uninstall the following kernel\(s\):
        .*
        .* is the current running kernel\.
        If you cannot guarantee that other kernels in this system are bootable and
        working properly, \*do not proceed\*\. You may end up with an unbootable system\.
        Do you want to proceed\? \(y/N\)
        """
        And stdout matches regexp:
        """
        The following package\(s\) will be REMOVED:
        (.|\n)+

        The following package\(s\) will be reinstalled from the archive:
        (.|\n)+

        Do you want to proceed\? \(y/N\)
        """
        When I reboot the machine
        Then I verify that `<fips-service>` is disabled
        When  I run `uname -r` as non-root
        Then stdout does not match regexp:
        """
        fips
        """
        And I verify that `openssh-server` is installed from apt source `<archive-source>`
        And I verify that `<kernel-package>` is not installed

        Examples: ubuntu release
           | release | machine_type  | fips-service | fips-name    | kernel-package   | fips-source                                                    | archive-source                                                    |
           | xenial  | lxd-vm        | fips         | FIPS         | linux-fips       | https://esm.ubuntu.com/fips/ubuntu xenial/main                 | https://esm.ubuntu.com/infra/ubuntu xenial-infra-security/main    |
           | xenial  | lxd-vm        | fips-updates | FIPS Updates | linux-fips       | https://esm.ubuntu.com/fips-updates/ubuntu xenial-updates/main | https://esm.ubuntu.com/infra/ubuntu xenial-infra-security/main    |
           | bionic  | lxd-vm        | fips         | FIPS         | linux-fips       | https://esm.ubuntu.com/fips/ubuntu bionic/main                 | https://esm.ubuntu.com/infra/ubuntu bionic-infra-security/main    |
           | bionic  | lxd-vm        | fips-updates | FIPS Updates | linux-fips       | https://esm.ubuntu.com/fips-updates/ubuntu bionic-updates/main | https://esm.ubuntu.com/infra/ubuntu bionic-infra-security/main    |
           | bionic  | aws.generic   | fips         | FIPS         | linux-aws-fips   | https://esm.ubuntu.com/fips/ubuntu bionic/main                 | https://esm.ubuntu.com/infra/ubuntu bionic-infra-security/main    |
           | bionic  | aws.generic   | fips-updates | FIPS Updates | linux-aws-fips   | https://esm.ubuntu.com/fips-updates/ubuntu bionic-updates/main | https://esm.ubuntu.com/infra/ubuntu bionic-infra-security/main    |
           | bionic  | azure.generic | fips         | FIPS         | linux-azure-fips | https://esm.ubuntu.com/fips/ubuntu bionic/main                 | https://esm.ubuntu.com/infra/ubuntu bionic-infra-security/main    |
           | bionic  | azure.generic | fips-updates | FIPS Updates | linux-azure-fips | https://esm.ubuntu.com/fips-updates/ubuntu bionic-updates/main | https://esm.ubuntu.com/infra/ubuntu bionic-infra-security/main    |
           | bionic  | gcp.generic   | fips         | FIPS         | linux-gcp-fips   | https://esm.ubuntu.com/fips/ubuntu bionic/main                 | https://esm.ubuntu.com/infra/ubuntu bionic-infra-security/main    |
           | bionic  | gcp.generic   | fips-updates | FIPS Updates | linux-gcp-fips   | https://esm.ubuntu.com/fips-updates/ubuntu bionic-updates/main | https://esm.ubuntu.com/infra/ubuntu bionic-infra-security/main    |
           | focal   | lxd-vm        | fips         | FIPS         | linux-fips       | https://esm.ubuntu.com/fips/ubuntu focal/main                  | http://archive.ubuntu.com/ubuntu focal-updates/main               |
           | focal   | lxd-vm        | fips-updates | FIPS Updates | linux-fips       | https://esm.ubuntu.com/fips-updates/ubuntu focal-updates/main  | http://archive.ubuntu.com/ubuntu focal-updates/main               |
           | focal   | aws.generic   | fips         | FIPS         | linux-aws-fips   | https://esm.ubuntu.com/fips/ubuntu focal/main                  | http://us-east-2.ec2.archive.ubuntu.com/ubuntu focal-updates/main |
           | focal   | aws.generic   | fips-updates | FIPS Updates | linux-aws-fips   | https://esm.ubuntu.com/fips-updates/ubuntu focal-updates/main  | http://us-east-2.ec2.archive.ubuntu.com/ubuntu focal-updates/main |
           | focal   | azure.generic | fips         | FIPS         | linux-azure-fips | https://esm.ubuntu.com/fips/ubuntu focal/main                  | http://azure.archive.ubuntu.com/ubuntu focal-updates/main         |
           | focal   | azure.generic | fips-updates | FIPS Updates | linux-azure-fips | https://esm.ubuntu.com/fips-updates/ubuntu focal-updates/main  | http://azure.archive.ubuntu.com/ubuntu focal-updates/main         |
           | focal   | gcp.generic   | fips         | FIPS         | linux-gcp-fips   | https://esm.ubuntu.com/fips/ubuntu focal/main                  | http://us-west2.gce.archive.ubuntu.com/ubuntu focal-updates/main  |
           | focal   | gcp.generic   | fips-updates | FIPS Updates | linux-gcp-fips   | https://esm.ubuntu.com/fips-updates/ubuntu focal-updates/main  | http://us-west2.gce.archive.ubuntu.com/ubuntu focal-updates/main  |

    @slow
    Scenario Outline: Disable does not purge if no other kernel found
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I apt update
        And I run `pro enable fips --assume-yes` with sudo
        And I reboot the machine
        And I run shell command `rm -rf $(find /boot -name 'vmlinuz*[^fips]')` with sudo
        And I verify that running `pro disable fips --purge` `with sudo` exits `1`
        Then stdout matches regexp:
        """
        \(The --purge flag is still experimental - use with caution\)

        Purging the FIPS packages would uninstall the following kernel\(s\):
        .*
        .* is the current running kernel\.
        No other valid Ubuntu kernel was found in the system\.
        Removing the package would potentially make the system unbootable\.
        Aborting\.
        """

        Examples: ubuntu release
           | release | machine_type |
           | xenial  | lxd-vm       |
           | bionic  | lxd-vm       |
           | focal   | lxd-vm       |
