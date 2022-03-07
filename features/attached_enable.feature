@uses.config.contract_token
Feature: Enable command behaviour when attached to an UA subscription

    @slow
    @series.xenial
    @series.bionic
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached enable Common Criteria service in an ubuntu lxd container
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua enable cc-eal` `as non-root` exits `1`
        And I will see the following on stderr:
            """
            This command must be run as root (try using sudo).
            """
        When I run `ua enable cc-eal` with sudo
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            Updating package lists
            (This will download more than 500MB of packages, so may take some time.)
            Installing CC EAL2 packages
            CC EAL2 enabled
            Please follow instructions in /usr/share/doc/ubuntu-commoncriteria/README to configure EAL2
            """
        Examples: ubuntu release
            | release |
            | xenial  |
            | bionic  |

    @series.focal
    @series.impish
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached enable Common Criteria service in an ubuntu lxd container
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua enable cc-eal` `as non-root` exits `1`
        And I will see the following on stderr:
            """
            This command must be run as root (try using sudo).
            """
        When I verify that running `ua enable cc-eal` `with sudo` exits `1`
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            CC EAL2 is not available for Ubuntu <version> (<full_name>).
            """
        Examples: ubuntu release
            | release | version    | full_name     |
            | focal   | 20.04 LTS  | Focal Fossa   |
            | impish  | 21.10      | Impish Indri  |

    @series.xenial
    @series.bionic
    @series.focal
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached enable of different services using json format
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua enable foobar --format json` `as non-root` exits `1`
        And stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
            """
            {"_schema_version": "0.1", "errors": [{"message": "json formatted response requires --assume-yes flag.", "message_code": "json-format-require-assume-yes", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
            """
        Then I verify that running `ua enable foobar --format json` `with sudo` exits `1`
        And stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
            """
            {"_schema_version": "0.1", "errors": [{"message": "json formatted response requires --assume-yes flag.", "message_code": "json-format-require-assume-yes", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
            """
        Then I verify that running `ua enable foobar --format json --assume-yes` `as non-root` exits `1`
        And stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
            """
            {"_schema_version": "0.1", "errors": [{"message": "This command must be run as root (try using sudo).", "message_code": "nonroot-user", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
            """
        And I verify that running `ua enable foobar --format json --assume-yes` `with sudo` exits `1`
        And stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
            """
            {"_schema_version": "0.1", "errors": [{"message": "Cannot enable unknown service 'foobar'.\nTry <valid_services>", "message_code": "invalid-service-or-failure", "service": null, "type": "system"}], "failed_services": ["foobar"], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
            """
        And I verify that running `ua enable ros foobar --format json --assume-yes` `with sudo` exits `1`
        And stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
        """
        {"_schema_version": "0.1", "errors": [{"message": "Cannot enable unknown service 'foobar, ros'.\nTry <valid_services>", "message_code": "invalid-service-or-failure", "service": null, "type": "system"}], "failed_services": ["foobar", "ros"], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
        """
        And I verify that running `ua enable esm-infra --format json --assume-yes` `with sudo` exits `1`
        And stdout is a json matching the `ua_operation` schema
        Then I will see the following on stdout:
            """
            {"_schema_version": "0.1", "errors": [{"message": "UA Infra: ESM is already enabled.\nSee: sudo ua status", "message_code": "service-already-enabled", "service": "esm-infra", "type": "service"}], "failed_services": ["esm-infra"], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
            """
        When I run `ua disable esm-infra` with sudo
        And I run `ua enable esm-infra --format json --assume-yes` with sudo
        Then stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
        """
        {"_schema_version": "0.1", "errors": [], "failed_services": [], "needs_reboot": false, "processed_services": ["esm-infra"], "result": "success", "warnings": []}
        """
        When I run `ua disable esm-infra` with sudo
        And I verify that running `ua enable esm-infra foobar --format json --assume-yes` `with sudo` exits `1`
        Then stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
        """
        {"_schema_version": "0.1", "errors": [{"message": "Cannot enable unknown service 'foobar'.\nTry <valid_services>", "message_code": "invalid-service-or-failure", "service": null, "type": "system"}], "failed_services": ["foobar"], "needs_reboot": false, "processed_services": ["esm-infra"], "result": "failure", "warnings": []}
        """
        When I run `ua disable esm-infra esm-apps` with sudo
        And I run `ua enable esm-infra esm-apps --beta --format json --assume-yes` with sudo
        Then stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
        """
        {"_schema_version": "0.1", "errors": [], "failed_services": [], "needs_reboot": false, "processed_services": ["esm-apps", "esm-infra"], "result": "success", "warnings": []}
        """

        Examples: ubuntu release
           | release | valid_services                                         |
           | xenial  | cc-eal, cis, esm-infra, fips, fips-updates, livepatch. |
           | bionic  | cc-eal, cis, esm-infra, fips, fips-updates, livepatch. |
           | focal   | cc-eal, esm-infra, fips, fips-updates, livepatch, usg. |

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached enable of a service in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua enable foobar` `as non-root` exits `1`
        And I will see the following on stderr:
            """
            This command must be run as root (try using sudo).
            """
        And I verify that running `ua enable foobar` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            One moment, checking your subscription first
            """
        And stderr matches regexp:
            """
            Cannot enable unknown service 'foobar'.
            Try cc-eal, cis, esm-infra, fips, fips-updates, livepatch.
            """
        And I verify that running `ua enable ros foobar` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            One moment, checking your subscription first
            """
        And stderr matches regexp:
            """
            Cannot enable unknown service 'foobar, ros'.
            Try cc-eal, cis, esm-infra, fips, fips-updates, livepatch.
            """
        And I verify that running `ua enable esm-infra` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            One moment, checking your subscription first
            UA Infra: ESM is already enabled.
            See: sudo ua status
            """
        When I run `apt-cache policy` with sudo
        Then apt-cache policy for the following url has permission `500`
        """
        <esm-infra-url> <release>-infra-updates/main amd64 Packages
        """
        And I verify that running `apt update` `with sudo` exits `0`
        When I run `apt install -y <infra-pkg>` with sudo, retrying exit [100]
        And I run `apt-cache policy <infra-pkg>` as non-root
        Then stdout matches regexp:
        """
        \s*500 <esm-infra-url> <release>-infra-security/main amd64 Packages
        \s*500 <esm-infra-url> <release>-infra-updates/main amd64 Packages
        """

        Examples: ubuntu release
           | release | infra-pkg | esm-infra-url                       |
           | bionic  | libkrad0  | https://esm.ubuntu.com/infra/ubuntu |
           | xenial  | libkrad0  | https://esm.ubuntu.com/infra/ubuntu |

    @series.focal
    @uses.config.machine_type.lxd.container
    Scenario: Attached enable of a service in a ubuntu machine
        Given a `focal` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua enable foobar` `as non-root` exits `1`
        And I will see the following on stderr:
            """
            This command must be run as root (try using sudo).
            """
        And I verify that running `ua enable foobar` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            One moment, checking your subscription first
            """
        And stderr matches regexp:
            """
            Cannot enable unknown service 'foobar'.
            Try cc-eal, esm-infra, fips, fips-updates, livepatch, usg.
            """
        And I verify that running `ua enable ros foobar` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            One moment, checking your subscription first
            """
        And stderr matches regexp:
            """
            Cannot enable unknown service 'foobar, ros'.
            Try cc-eal, esm-infra, fips, fips-updates, livepatch, usg.
            """
        And I verify that running `ua enable esm-infra` `with sudo` exits `1`
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            UA Infra: ESM is already enabled.
            See: sudo ua status
            """
        When I run `apt-cache policy` with sudo
        Then apt-cache policy for the following url has permission `500`
        """
        https://esm.ubuntu.com/infra/ubuntu focal-infra-updates/main amd64 Packages
        """
        And I verify that running `apt update` `with sudo` exits `0`
        When I run `apt install -y hello` with sudo, retrying exit [100]
        And I run `apt-cache policy hello` as non-root
        Then stdout matches regexp:
        """
        \s*500 https://esm.ubuntu.com/infra/ubuntu focal-infra-security/main amd64 Packages
        \s*500 https://esm.ubuntu.com/infra/ubuntu focal-infra-updates/main amd64 Packages
        """

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline:  Attached enable of non-container services in a ubuntu lxd container
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua enable livepatch` `as non-root` exits `1`
        And I will see the following on stderr:
            """
            This command must be run as root (try using sudo).
            """
        And I verify that running `ua enable livepatch` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            One moment, checking your subscription first
            Cannot install Livepatch on a container.
            """

        Examples: Un-supported services in containers
           | release |
           | bionic  |
           | focal   |
           | xenial  |
           | impish  |
           | jammy   |

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached enable not entitled service in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I create the file `/tmp/machine-token-overlay.json` with the following:
        """
        {
            "machineTokenInfo": {
                "contractInfo": {
                    "resourceEntitlements": [
                        {
                            "type": "esm-apps",
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
        """
        When I attach `contract_token` with sudo
        Then I verify that running `ua enable esm-apps` `as non-root` exits `1`
        And I will see the following on stderr:
            """
            This command must be run as root (try using sudo).
            """
        And I verify that running `ua enable esm-apps --beta` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            One moment, checking your subscription first
            This subscription is not entitled to UA Apps: ESM
            For more information see: https://ubuntu.com/advantage.
            """

        Examples: not entitled services
           | release |
           | bionic  |
           | focal   |
           | xenial  |

    @series.xenial
    @series.bionic
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached enable of cis service in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I verify that running `ua enable cis` `with sudo` exits `0`
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            Updating package lists
            Installing CIS Audit packages
            CIS Audit enabled
            Visit https://ubuntu.com/security/cis to learn how to use CIS
            """
        When I run `apt-cache policy usg-cisbenchmark` as non-root
        Then stdout does not match regexp:
        """
        .*Installed: \(none\)
        """
        And stdout matches regexp:
        """
        \s* 500 https://esm.ubuntu.com/cis/ubuntu <release>/main amd64 Packages
        """
        When I run `apt-cache policy usg-common` as non-root
        Then stdout does not match regexp:
        """
        .*Installed: \(none\)
        """
        And stdout matches regexp:
        """
        \s* 500 https://esm.ubuntu.com/cis/ubuntu <release>/main amd64 Packages
        """
        When I verify that running `ua enable cis` `with sudo` exits `1`
        Then stdout matches regexp
        """
        One moment, checking your subscription first
        CIS Audit is already enabled.
        See: sudo ua status
        """
        When I run `cis-audit level1_server` with sudo
        Then stdout matches regexp
        """
        Title.*Ensure no duplicate UIDs exist
        Rule.*xccdf_com.ubuntu.<release>.cis_rule_CIS-.*
        Result.*pass
        """
        And stdout matches regexp:
        """
        Title.*Ensure default user umask is 027 or more restrictive
        Rule.*xccdf_com.ubuntu.<release>.cis_rule_CIS-.*
        Result.*fail
        """
        And stdout matches regexp
        """
        CIS audit scan completed
        """
        When I verify that running `/usr/share/ubuntu-scap-security-guides/cis-hardening/<cis_script> lvl1_server` `with sudo` exits `0`
        And I run `cis-audit level1_server` with sudo
        Then stdout matches regexp:
        """
        Title.*Ensure default user umask is 027 or more restrictive
        Rule.*xccdf_com.ubuntu.<release>.cis_rule_CIS-.*
        Result.*pass
        """
        And stdout matches regexp
        """
        CIS audit scan completed
        """

        Examples: cis script
           | release | cis_script                                  |
           | bionic  | Canonical_Ubuntu_18.04_CIS-harden.sh        |
           | xenial  | Canonical_Ubuntu_16.04_CIS_v1.1.0-harden.sh |

    @series.focal
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached enable of cis service in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I verify that running `ua enable cis` `with sudo` exits `0`
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            From Ubuntu 20.04 and onwards 'ua enable cis' has been
            replaced by 'ua enable usg'. See more information at:
            https://ubuntu.com/security/certifications/docs/usg
            Updating package lists
            Installing CIS Audit packages
            CIS Audit enabled
            Visit https://ubuntu.com/security/cis to learn how to use CIS
            """
        When I run `apt-cache policy usg-cisbenchmark` as non-root
        Then stdout does not match regexp:
        """
        .*Installed: \(none\)
        """
        And stdout matches regexp:
        """
        \s* 500 https://esm.ubuntu.com/cis/ubuntu <release>/main amd64 Packages
        """
        When I run `apt-cache policy usg-common` as non-root
        Then stdout does not match regexp:
        """
        .*Installed: \(none\)
        """
        And stdout matches regexp:
        """
        \s* 500 https://esm.ubuntu.com/cis/ubuntu <release>/main amd64 Packages
        """
        When I verify that running `ua enable cis` `with sudo` exits `1`
        Then stdout matches regexp
        """
        One moment, checking your subscription first
        From Ubuntu 20.04 and onwards 'ua enable cis' has been
        replaced by 'ua enable usg'. See more information at:
        https://ubuntu.com/security/certifications/docs/usg
        CIS Audit is already enabled.
        See: sudo ua status
        """
        When I run `cis-audit level1_server` with sudo
        Then stdout matches regexp
        """
        Title.*Ensure no duplicate UIDs exist
        Rule.*xccdf_com.ubuntu.<release>.cis_rule_CIS-.*
        Result.*pass
        """
        And stdout matches regexp:
        """
        Title.*Ensure default user umask is 027 or more restrictive
        Rule.*xccdf_com.ubuntu.<release>.cis_rule_CIS-.*
        Result.*fail
        """
        And stdout matches regexp
        """
        CIS audit scan completed
        """
        When I verify that running `/usr/share/ubuntu-scap-security-guides/cis-hardening/<cis_script> lvl1_server` `with sudo` exits `0`
        And I run `cis-audit level1_server` with sudo
        Then stdout matches regexp:
        """
        Title.*Ensure default user umask is 027 or more restrictive
        Rule.*xccdf_com.ubuntu.<release>.cis_rule_CIS-.*
        Result.*pass
        """
        And stdout matches regexp
        """
        CIS audit scan completed
        """

        Examples: cis script
           | release | cis_script                                  |
           | focal   | Canonical_Ubuntu_20.04_CIS-harden.sh        |

    @series.bionic
    @series.xenial
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached enable of usg service in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I verify that running `ua enable usg` `with sudo` exits `1`
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            """
        Then I will see the following on stderr:
            """
            Cannot enable unknown service 'usg'.
            Try cc-eal, cis, esm-infra, fips, fips-updates, livepatch.
            """

        Examples: cis service
           | release |
           | bionic  |
           | xenial  |

    @series.focal
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached enable of usg service in a focal machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua enable usg` with sudo
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            Updating package lists
            Ubuntu Security Guide enabled
            Visit https://ubuntu.com/security/certifications/docs/usg for the next steps
            """
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            usg         +yes    +enabled   +Security compliance and audit tools
            """
        When I run `ua disable usg` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            """
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            usg         +yes    +disabled   +Security compliance and audit tools
            """
        When I run `ua enable cis` with sudo
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            From Ubuntu 20.04 and onwards 'ua enable cis' has been
            replaced by 'ua enable usg'. See more information at:
            https://ubuntu.com/security/certifications/docs/usg
            Updating package lists
            Installing CIS Audit packages
            CIS Audit enabled
            Visit https://ubuntu.com/security/cis to learn how to use CIS
            """
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            usg         +yes    +enabled   +Security compliance and audit tools
            """
        When I run `ua disable usg` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            """
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            usg         +yes    +disabled   +Security compliance and audit tools
            """

        Examples: cis service
           | release |
           | focal  |

    @series.bionic
    @series.xenial
    @uses.config.machine_type.lxd.vm
    Scenario Outline: Attached disable of livepatch in a lxd vm
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua status` with sudo
        Then stdout matches regexp:
        """
        esm-apps     +yes      +enabled  +UA Apps: Extended Security Maintenance \(ESM\)
        esm-infra    +yes      +enabled  +UA Infra: Extended Security Maintenance \(ESM\)
        fips         +yes      +disabled +NIST-certified core packages
        fips-updates +yes      +disabled +NIST-certified core packages with priority security updates
        livepatch    +yes      +enabled  +Canonical Livepatch service
        """
        When I run `ua disable livepatch` with sudo
        Then I verify that running `canonical-livepatch status` `with sudo` exits `1`
        And stderr matches regexp:
        """
        Machine is not enabled. Please run 'sudo canonical-livepatch enable' with the
        token obtained from https://ubuntu.com/livepatch.
        """
        When I run `ua status` with sudo
        Then stdout matches regexp:
        """
        esm-apps     +yes      +enabled  +UA Apps: Extended Security Maintenance \(ESM\)
        esm-infra    +yes      +enabled  +UA Infra: Extended Security Maintenance \(ESM\)
        fips         +yes      +disabled +NIST-certified core packages
        fips-updates +yes      +disabled +NIST-certified core packages with priority security updates
        livepatch    +yes      +disabled +Canonical Livepatch service
        """

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |

    @series.bionic
    @series.xenial
    @uses.config.machine_type.lxd.vm
    Scenario Outline: Attached enable livepatch
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I verify that running `canonical-livepatch status` `with sudo` exits `1`
        Then I will see the following on stderr:
            """
            sudo: canonical-livepatch: command not found
            """
        When I attach `contract_token` with sudo
        Then stdout matches regexp:
            """
            Installing canonical-livepatch snap
            Canonical livepatch enabled
            """
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            livepatch     yes                enabled
            """
        When I run `canonical-livepatch status` with sudo
        Then stdout matches regexp:
            """
            running: true
            """

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |

    @slow
    @series.bionic
    @uses.config.machine_type.lxd.vm
    Scenario: Attached enable livepatch on a machine with fips active
        Given a `bionic` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            UA Infra: ESM enabled
            Installing canonical-livepatch snap
            Canonical livepatch enabled
            """
        When I run `ua disable livepatch` with sudo
        And I run `ua enable fips --assume-yes` with sudo
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            Updating package lists
            Installing FIPS packages
            FIPS enabled
            A reboot is required to complete install.
            """
        When I append the following on uaclient config:
            """
            features:
              block_disable_on_enable: true
            """
        Then I verify that running `ua enable livepatch` `with sudo` exits `1`
        And I will see the following on stdout
            """
            One moment, checking your subscription first
            Cannot enable Livepatch when FIPS is enabled.
            """
        Then I verify that running `ua enable livepatch --format json --assume-yes` `with sudo` exits `1`
        And I will see the following on stdout
            """
            {"_schema_version": "0.1", "errors": [{"message": "Cannot enable Livepatch when FIPS is enabled.", "message_code": "livepatch-error-when-fips-enabled", "service": "livepatch", "type": "service"}], "failed_services": ["livepatch"], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
            """

    @series.bionic
    @uses.config.machine_type.lxd.vm
    Scenario: Attached enable fips on a machine with livepatch active
        Given a `bionic` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            UA Infra: ESM enabled
            Installing canonical-livepatch snap
            Canonical livepatch enabled
            """
        When I append the following on uaclient config:
        """
        features:
          block_disable_on_enable: true
        """
        Then I verify that running `ua enable fips --assume-yes` `with sudo` exits `1`
        And I will see the following on stdout
            """
            One moment, checking your subscription first
            Cannot enable FIPS when Livepatch is enabled.
            """
        Then I verify that running `ua enable fips --assume-yes --format json` `with sudo` exits `1`
        And stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
        """
        {"_schema_version": "0.1", "errors": [{"message": "Cannot enable FIPS when Livepatch is enabled.", "service": "fips", "type": "service"}], "failed_services": ["fips"], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
        """

    @slow
    @series.xenial
    @series.bionic
    @uses.config.machine_type.lxd.vm
    Scenario Outline: Attached enable fips on a machine with livepatch active
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            UA Infra: ESM enabled
            """
        And stdout matches regexp:
            """
            Installing canonical-livepatch snap
            Canonical livepatch enabled
            """
        When I run `ua enable fips --assume-yes` with sudo
        Then I will see the following on stdout
            """
            One moment, checking your subscription first
            Updating package lists
            Installing FIPS packages
            FIPS enabled
            A reboot is required to complete install.
            """
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            fips +yes +enabled
            """
        And stdout matches regexp:
            """
            livepatch +yes +n/a
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | xenial  |

    @slow
    @series.xenial
    @series.bionic
    @uses.config.machine_type.lxd.vm
    Scenario Outline: Attached enable fips on a machine with fips-updates active
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then stdout matches regexp:
            """
            UA Infra: ESM enabled
            """
        And stdout matches regexp:
            """
            Installing canonical-livepatch snap
            Canonical livepatch enabled
            """
        When I run `ua disable livepatch` with sudo
        And I run `ua enable fips-updates --assume-yes` with sudo
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            Updating package lists
            Installing FIPS Updates packages
            FIPS Updates enabled
            A reboot is required to complete install.
            """
        When I verify that running `ua enable fips --assume-yes` `with sudo` exits `1`
        Then I will see the following on stdout
            """
            One moment, checking your subscription first
            Cannot enable FIPS when FIPS Updates is enabled.
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | xenial  |

    @series.xenial
    @series.bionic
    @uses.config.contract_token
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached enable ros on a machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua status --all` as non-root
        Then stdout matches regexp
        """
        ros           yes                disabled           Security Updates for the Robot Operating System
        """
        When I run `ua enable ros --assume-yes --beta` with sudo
        And I run `ua status --all` as non-root
        Then stdout matches regexp
        """
        ros           yes                enabled            Security Updates for the Robot Operating System
        """
        And stdout matches regexp
        """
        esm-apps      yes                enabled            UA Apps: Extended Security Maintenance \(ESM\)
        """
        And stdout matches regexp
        """
        esm-infra     yes                enabled            UA Infra: Extended Security Maintenance \(ESM\)
        """
        When I verify that running `ua disable esm-apps` `with sudo` and stdin `N` exits `1`
        Then stdout matches regexp
        """
        ROS ESM Security Updates depends on UA Apps: ESM.
        Disable ROS ESM Security Updates and proceed to disable UA Apps: ESM\? \(y\/N\) Cannot disable UA Apps: ESM when ROS ESM Security Updates is enabled.
        """
        When I run `ua disable esm-apps` `with sudo` and stdin `y`
        Then stdout matches regexp
        """
        ROS ESM Security Updates depends on UA Apps: ESM.
        Disable ROS ESM Security Updates and proceed to disable UA Apps: ESM\? \(y\/N\) Disabling dependent service: ROS ESM Security Updates
        Updating package lists
        """
        When I run `ua status --all` as non-root
        Then stdout matches regexp
        """
        ros           yes                disabled           Security Updates for the Robot Operating System
        """
        And stdout matches regexp
        """
        esm-apps      yes                disabled           UA Apps: Extended Security Maintenance \(ESM\)
        """
        When I verify that running `ua enable ros --beta` `with sudo` and stdin `N` exits `1`
        Then stdout matches regexp
        """
        ROS ESM Security Updates cannot be enabled with UA Apps: ESM disabled.
        Enable UA Apps: ESM and proceed to enable ROS ESM Security Updates\? \(y\/N\) Cannot enable ROS ESM Security Updates when UA Apps: ESM is disabled.
        """
        When I run `ua enable ros --beta` `with sudo` and stdin `y`
        Then stdout matches regexp
        """
        One moment, checking your subscription first
        ROS ESM Security Updates cannot be enabled with UA Apps: ESM disabled.
        Enable UA Apps: ESM and proceed to enable ROS ESM Security Updates\? \(y\/N\) Enabling required service: UA Apps: ESM
        UA Apps: ESM enabled
        Updating package lists
        ROS ESM Security Updates enabled
        """
        When I run `ua status --all` as non-root
        Then stdout matches regexp
        """
        ros           yes                enabled            Security Updates for the Robot Operating System
        """
        And stdout matches regexp
        """
        esm-apps      yes                enabled            UA Apps: Extended Security Maintenance \(ESM\)
        """
        And stdout matches regexp
        """
        esm-infra     yes                enabled            UA Infra: Extended Security Maintenance \(ESM\)
        """
        When I run `apt-cache policy` as non-root
        Then apt-cache policy for the following url has permission `500`
        """
        <ros-security-source> amd64 Packages
        """
        When I run `apt install python3-catkin-pkg -y` with sudo
        Then I verify that `python3-catkin-pkg` is installed from apt source `<ros-security-source>`

        When I run `ua enable ros-updates --assume-yes --beta` with sudo
        And I run `ua status --all` as non-root
        Then stdout matches regexp
        """
        ros-updates   yes                enabled            All Updates for the Robot Operating System
        """
        When I run `apt-cache policy` as non-root
        Then apt-cache policy for the following url has permission `500`
        """
        <ros-updates-source> amd64 Packages
        """
        When I run `apt install python3-catkin-pkg -y` with sudo
        Then I verify that `python3-catkin-pkg` is installed from apt source `<ros-updates-source>`
        When I run `ua disable ros` `with sudo` and stdin `y`
        Then stdout matches regexp
        """
        ROS ESM All Updates depends on ROS ESM Security Updates.
        Disable ROS ESM All Updates and proceed to disable ROS ESM Security Updates\? \(y\/N\) Disabling dependent service: ROS ESM All Updates
        Updating package lists
        """
        When I run `ua enable ros-updates --beta` `with sudo` and stdin `y`
        Then stdout matches regexp
        """
        One moment, checking your subscription first
        ROS ESM All Updates cannot be enabled with ROS ESM Security Updates disabled.
        Enable ROS ESM Security Updates and proceed to enable ROS ESM All Updates\? \(y\/N\) Enabling required service: ROS ESM Security Updates
        ROS ESM Security Updates enabled
        Updating package lists
        ROS ESM All Updates enabled
        """
        When I run `ua status --all` as non-root
        Then stdout matches regexp
        """
        ros-updates   yes                enabled            All Updates for the Robot Operating System
        """
        And stdout matches regexp
        """
        ros           yes                enabled            Security Updates for the Robot Operating System
        """
        When I run `ua disable ros-updates --assume-yes` with sudo
        When I run `ua disable ros --assume-yes` with sudo
        When I run `ua disable esm-apps --assume-yes` with sudo
        When I run `ua disable esm-infra --assume-yes` with sudo
        When I run `ua enable ros-updates --assume-yes --beta` with sudo
        When I run `ua status --all` as non-root
        Then stdout matches regexp
        """
        ros-updates   yes                enabled            All Updates for the Robot Operating System
        """
        And stdout matches regexp
        """
        ros           yes                enabled            Security Updates for the Robot Operating System
        """
        And stdout matches regexp
        """
        esm-apps      yes                enabled            UA Apps: Extended Security Maintenance \(ESM\)
        """
        And stdout matches regexp
        """
        esm-infra     yes                enabled            UA Infra: Extended Security Maintenance \(ESM\)
        """
        When I run `ua detach` `with sudo` and stdin `y`
        Then stdout matches regexp:
        """
        Updating package lists
        Updating package lists
        Updating package lists
        Updating package lists
        This machine is now detached.
        """

        Examples: ubuntu release
           | release | ros-security-source                                    | ros-updates-source                                            |
           | xenial  | https://esm.ubuntu.com/ros/ubuntu xenial-security/main | https://esm.ubuntu.com/ros-updates/ubuntu xenial-updates/main |
           | bionic  | https://esm.ubuntu.com/ros/ubuntu bionic-security/main | https://esm.ubuntu.com/ros-updates/ubuntu bionic-updates/main |
