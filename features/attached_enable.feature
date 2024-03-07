@uses.config.contract_token
Feature: Enable command behaviour when attached to an Ubuntu Pro subscription

  Scenario Outline: Attached enable Common Criteria service in an ubuntu lxd container
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then I verify that running `pro enable cc-eal` `as non-root` exits `1`
    And I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    When I run `pro enable cc-eal` with sudo
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Updating CC EAL2 package lists
      (This will download more than 500MB of packages, so may take some time.)
      Updating standard Ubuntu package lists
      Installing CC EAL2 packages
      CC EAL2 enabled
      Please follow instructions in /usr/share/doc/ubuntu-commoncriteria/README to configure EAL2
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | bionic  | wsl           |

  Scenario Outline: Enable cc-eal with --access-only
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    When I run `pro enable cc-eal --access-only` with sudo
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Updating CC EAL2 package lists
      Skipping installing packages: ubuntu-commoncriteria
      CC EAL2 access enabled
      """
    Then I verify that running `apt-get install ubuntu-commoncriteria` `with sudo` exits `0`

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |

  Scenario Outline: Attached enable Common Criteria service in an ubuntu lxd container
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then I verify that running `pro enable cc-eal` `as non-root` exits `1`
    And I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    When I verify that running `pro enable cc-eal` `with sudo` exits `1`
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      CC EAL2 is not available for Ubuntu <version> (<full_name>).
      """

    Examples: ubuntu release
      | release | machine_type  | version   | full_name       |
      | focal   | lxd-container | 20.04 LTS | Focal Fossa     |
      | jammy   | lxd-container | 22.04 LTS | Jammy Jellyfish |
      | mantic  | lxd-container | 23.10     | Mantic Minotaur |

  Scenario Outline: Empty series affordance means no series, null means all series
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    When I set the machine token overlay to the following yaml
      """
      machineTokenInfo:
        contractInfo:
          resourceEntitlements:
            - type: esm-infra
              affordances:
                series: []
      """
    When I verify that running `pro enable esm-infra` `with sudo` exits `1`
    Then stdout matches regexp:
      """
      One moment, checking your subscription first
      Ubuntu Pro: ESM Infra is not available for Ubuntu .*
      """
    When I create the file `/var/lib/ubuntu-advantage/machine-token-overlay.json` with the following:
      """
      {
          "machineTokenInfo": {
              "contractInfo": {
                  "resourceEntitlements": [
                      {
                          "type": "esm-infra",
                          "affordances": {
                              "series": null
                          }
                      }
                  ]
              }
          }
      }
      """
    When I verify that running `pro enable esm-infra` `with sudo` exits `0`
    Then stdout matches regexp:
      """
      One moment, checking your subscription first
      Updating Ubuntu Pro: ESM Infra package lists
      Ubuntu Pro: ESM Infra enabled
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |

  Scenario Outline: Attached enable of different services using json format
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
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
    Then I verify that running `pro enable foobar --format json --assume-yes` `as non-root` exits `1`
    And stdout is a json matching the `ua_operation` schema
    And I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [{"message": "This command must be run as root (try using sudo).", "message_code": "nonroot-user", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
      """
    And I verify that running `pro enable foobar --format json --assume-yes` `with sudo` exits `1`
    And stdout is a json matching the `ua_operation` schema
    And I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [{"additional_info": {"invalid_service": "foobar", "operation": "enable", "service_msg": "Try <valid_services>"}, "message": "Cannot enable unknown service 'foobar'.\nTry <valid_services>", "message_code": "invalid-service-or-failure", "service": null, "type": "system"}], "failed_services": ["foobar"], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
      """
    And I verify that running `pro enable blah foobar --format json --assume-yes` `with sudo` exits `1`
    And stdout is a json matching the `ua_operation` schema
    And I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [{"additional_info": {"invalid_service": "blah, foobar", "operation": "enable", "service_msg": "Try <valid_services>"}, "message": "Cannot enable unknown service 'blah, foobar'.\nTry <valid_services>", "message_code": "invalid-service-or-failure", "service": null, "type": "system"}], "failed_services": ["blah", "foobar"], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
      """
    And I verify that running `pro enable esm-infra --format json --assume-yes` `with sudo` exits `1`
    And stdout is a json matching the `ua_operation` schema
    Then I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [{"message": "Ubuntu Pro: ESM Infra is already enabled.\nSee: sudo pro status", "message_code": "service-already-enabled", "service": "esm-infra", "type": "service"}], "failed_services": ["esm-infra"], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
      """
    When I run `pro disable esm-infra` with sudo
    And I run `pro enable esm-infra --format json --assume-yes` with sudo
    Then stdout is a json matching the `ua_operation` schema
    And I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [], "failed_services": [], "needs_reboot": false, "processed_services": ["esm-infra"], "result": "success", "warnings": []}
      """
    When I run `pro disable esm-infra` with sudo
    And I verify that running `pro enable esm-infra foobar --format json --assume-yes` `with sudo` exits `1`
    Then stdout is a json matching the `ua_operation` schema
    And I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [{"additional_info": {"invalid_service": "foobar", "operation": "enable", "service_msg": "Try <valid_services>"}, "message": "Cannot enable unknown service 'foobar'.\nTry <valid_services>", "message_code": "invalid-service-or-failure", "service": null, "type": "system"}], "failed_services": ["foobar"], "needs_reboot": false, "processed_services": ["esm-infra"], "result": "failure", "warnings": []}
      """
    When I run `pro disable esm-infra esm-apps` with sudo
    And I run `pro enable esm-infra esm-apps --beta --format json --assume-yes` with sudo
    Then stdout is a json matching the `ua_operation` schema
    And I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [], "failed_services": [], "needs_reboot": false, "processed_services": ["esm-apps", "esm-infra"], "result": "success", "warnings": []}
      """

    Examples: ubuntu release
      | release | machine_type  | valid_services                                                                                                                             |
      | xenial  | lxd-container | anbox-cloud, cc-eal, cis, esm-apps, esm-infra, fips, fips-preview,\nfips-updates, landscape, livepatch, realtime-kernel, ros, ros-updates. |
      | bionic  | lxd-container | anbox-cloud, cc-eal, cis, esm-apps, esm-infra, fips, fips-preview,\nfips-updates, landscape, livepatch, realtime-kernel, ros, ros-updates. |
      | focal   | lxd-container | anbox-cloud, cc-eal, esm-apps, esm-infra, fips, fips-preview, fips-updates,\nlandscape, livepatch, realtime-kernel, ros, ros-updates, usg. |
      | jammy   | lxd-container | anbox-cloud, cc-eal, esm-apps, esm-infra, fips, fips-preview, fips-updates,\nlandscape, livepatch, realtime-kernel, ros, ros-updates, usg. |

  Scenario Outline: Attached enable of a service in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then I verify that running `pro enable foobar` `as non-root` exits `1`
    And I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    And I verify that running `pro enable foobar` `with sudo` exits `1`
    And I will see the following on stdout:
      """
      One moment, checking your subscription first
      """
    And stderr matches regexp:
      """
      Cannot enable unknown service 'foobar'.
      <msg>
      """
    And I verify that running `pro enable blah foobar` `with sudo` exits `1`
    And I will see the following on stdout:
      """
      One moment, checking your subscription first
      """
    And stderr matches regexp:
      """
      Cannot enable unknown service 'blah, foobar'.
      <msg>
      """
    And I verify that running `pro enable esm-infra` `with sudo` exits `1`
    And I will see the following on stdout:
      """
      One moment, checking your subscription first
      Ubuntu Pro: ESM Infra is already enabled.
      See: sudo pro status
      """
    When I run `apt-cache policy` with sudo
    Then apt-cache policy for the following url has priority `510`
      """
      <esm-infra-url> <release>-infra-updates/main amd64 Packages
      """
    And apt-cache policy for the following url has priority `510`
      """
      <esm-infra-url> <release>-infra-security/main amd64 Packages
      """
    And I ensure apt update runs without errors
    When I apt install `<infra-pkg>`
    And I run `apt-cache policy <infra-pkg>` as non-root
    Then stdout matches regexp:
      """
      \s*510 <esm-infra-url> <release>-infra-security/main amd64 Packages
      """

    Examples: ubuntu release
      | release | machine_type  | infra-pkg | esm-infra-url                       | msg                                                                                                                                            |
      | xenial  | lxd-container | libkrad0  | https://esm.ubuntu.com/infra/ubuntu | Try anbox-cloud, cc-eal, cis, esm-apps, esm-infra, fips, fips-preview,\nfips-updates, landscape, livepatch, realtime-kernel, ros, ros-updates. |
      | bionic  | lxd-container | libkrad0  | https://esm.ubuntu.com/infra/ubuntu | Try anbox-cloud, cc-eal, cis, esm-apps, esm-infra, fips, fips-preview,\nfips-updates, landscape, livepatch, realtime-kernel, ros, ros-updates. |
      | focal   | lxd-container | hello     | https://esm.ubuntu.com/infra/ubuntu | Try anbox-cloud, cc-eal, esm-apps, esm-infra, fips, fips-preview, fips-updates,\nlandscape, livepatch, realtime-kernel, ros, ros-updates, usg. |

  Scenario Outline: Attached enable of non-container services in a ubuntu lxd container
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then I verify that running `pro enable livepatch` `as non-root` exits `1`
    And I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    And I verify that running `pro enable livepatch` `with sudo` exits `1`
    And I will see the following on stdout:
      """
      One moment, checking your subscription first
      Cannot install Livepatch on a container.
      """

    Examples: Un-supported services in containers
      | release | machine_type  |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | xenial  | lxd-container |
      | jammy   | lxd-container |
      | mantic  | lxd-container |

  Scenario Outline: Attached enable not entitled service in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I set the machine token overlay to the following yaml
      """
      machineTokenInfo:
        contractInfo:
          resourceEntitlements:
            - type: esm-apps
              entitled: false
      """
    When I attach `contract_token` with sudo
    Then I verify that running `pro enable esm-apps` `as non-root` exits `1`
    And I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    And I verify that running `pro enable esm-apps --beta` `with sudo` exits `1`
    And I will see the following on stdout:
      """
      One moment, checking your subscription first
      This subscription is not entitled to Ubuntu Pro: ESM Apps
      View your subscription at: https://ubuntu.com/pro/dashboard
      """

    Examples: not entitled services
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |

  Scenario Outline: Attached enable of cis service in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I verify that running `pro enable cis --access-only` `with sudo` exits `0`
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Updating CIS Audit package lists
      Skipping installing packages: usg-cisbenchmark usg-common
      CIS Audit access enabled
      Visit https://ubuntu.com/security/cis to learn how to use CIS
      """
    When I run `pro disable cis` with sudo
    And I verify that running `pro enable cis` `with sudo` exits `0`
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Updating CIS Audit package lists
      Updating standard Ubuntu package lists
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
    When I verify that running `pro enable cis` `with sudo` exits `1`
    Then stdout matches regexp
      """
      One moment, checking your subscription first
      CIS Audit is already enabled.
      See: sudo pro status
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
      | release | machine_type  | cis_script                                  |
      | bionic  | lxd-container | Canonical_Ubuntu_18.04_CIS-harden.sh        |
      | bionic  | wsl           | Canonical_Ubuntu_18.04_CIS-harden.sh        |
      | xenial  | lxd-container | Canonical_Ubuntu_16.04_CIS_v1.1.0-harden.sh |

  Scenario Outline: Attached enable of cis service in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I verify that running `pro enable cis` `with sudo` exits `0`
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      From Ubuntu 20.04 onward 'pro enable cis' has been
      replaced by 'pro enable usg'. See more information at:
      https://ubuntu.com/security/certifications/docs/usg
      Updating CIS Audit package lists
      Updating standard Ubuntu package lists
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
    When I verify that running `pro enable cis` `with sudo` exits `1`
    Then stdout matches regexp
      """
      One moment, checking your subscription first
      From Ubuntu 20.04 onward 'pro enable cis' has been
      replaced by 'pro enable usg'. See more information at:
      https://ubuntu.com/security/certifications/docs/usg
      CIS Audit is already enabled.
      See: sudo pro status
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

    Examples: cis service
      | release | machine_type  |
      | focal   | lxd-container |
      | focal   | wsl           |

  Scenario Outline: Attached enable of usg service in a focal machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I run `pro enable usg` with sudo
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Updating Ubuntu Security Guide package lists
      Ubuntu Security Guide enabled
      Visit https://ubuntu.com/security/certifications/docs/usg for the next steps
      """
    And I verify that `usg` is enabled
    When I run `pro disable usg` with sudo
    Then stdout matches regexp:
      """
      Updating package lists
      """
    And I verify that `usg` is disabled
    When I run `pro enable cis` with sudo
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      From Ubuntu 20.04 onward 'pro enable cis' has been
      replaced by 'pro enable usg'. See more information at:
      https://ubuntu.com/security/certifications/docs/usg
      Updating CIS Audit package lists
      Updating standard Ubuntu package lists
      Installing CIS Audit packages
      CIS Audit enabled
      Visit https://ubuntu.com/security/cis to learn how to use CIS
      """
    And I verify that `usg` is enabled
    When I run `pro disable usg` with sudo
    Then stdout matches regexp:
      """
      Updating package lists
      """
    And I verify that `usg` is disabled

    Examples: cis service
      | release | machine_type  |
      | focal   | lxd-container |
      | focal   | wsl           |

  Scenario Outline: Attached disable of livepatch in a lxd vm
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then I verify that `esm-apps` is enabled
    And I verify that `esm-infra` is enabled
    And I verify that `livepatch` status is `<livepatch_status>`
    When I run `pro disable livepatch` with sudo
    Then I verify that running `canonical-livepatch status` `with sudo` exits `1`
    And stderr matches regexp:
      """
      Machine is not enabled. Please run 'sudo canonical-livepatch enable' with the
      token obtained from https://ubuntu.com/livepatch.
      """
    And I verify that `esm-apps` is enabled
    And I verify that `esm-infra` is enabled
    And I verify that `livepatch` is disabled
    When I verify that running `pro enable livepatch --access-only` `with sudo` exits `1`
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Livepatch does not support being enabled with --access-only
      """

    Examples: ubuntu release
      | release | machine_type | livepatch_status |
      | xenial  | lxd-vm       | warning          |
      | bionic  | lxd-vm       | enabled          |

  Scenario Outline: Attach works when snapd cannot be installed
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I apt remove `snapd`
    And I create the file `/etc/apt/preferences.d/no-snapd` with the following
      """
      Package: snapd
      Pin: release o=*
      Pin-Priority: -10
      """
    And I apt update
    When I attempt to attach `contract_token` with sudo
    Then I will see the following on stderr:
      """
      Enabling default service esm-apps
      Enabling default service esm-infra
      Enabling default service livepatch
      Failed to enable default services, check: sudo pro status
      """
    And I verify that `livepatch` is disabled
    And I verify that running `pro enable livepatch` `with sudo` exits `1`
    And I will see the following on stdout:
      """
      One moment, checking your subscription first
      Installing snapd
      Updating standard Ubuntu package lists
      Failed to install snapd on the system
      """

    Examples: ubuntu release
      | release | machine_type |
      | xenial  | lxd-vm       |
      | bionic  | lxd-vm       |

  Scenario Outline: Attached enable livepatch
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I verify that running `canonical-livepatch status` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      sudo: canonical-livepatch: command not found
      """
    When I attach `contract_token` with sudo
    Then stdout matches regexp:
      """
      Installing canonical-livepatch snap
      Canonical Livepatch enabled
      """
    And I verify that `livepatch` status is `<livepatch_status>`
    When I run `canonical-livepatch status` with sudo
    Then stdout matches regexp:
      """
      running: true
      """

    Examples: ubuntu release
      | release | machine_type | livepatch_status |
      | xenial  | lxd-vm       | warning          |
      | bionic  | lxd-vm       | enabled          |

  Scenario Outline: Attached enable livepatch
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then stdout matches regexp:
      """
      Installing canonical-livepatch snap
      Canonical Livepatch enabled
      """
    And I verify that `livepatch` status is warning
    When I run `pro api u.pro.security.status.reboot_required.v1` with sudo
    Then stdout matches regexp:
      """
      {"_schema_version": "v1", "data": {"attributes": {"livepatch_enabled": true, "livepatch_enabled_and_kernel_patched": true, "livepatch_state": "applied", "livepatch_support": "kernel-upgrade-required", "reboot_required": "no", "reboot_required_packages": {"kernel_packages": null, "standard_packages": null}}, "meta": {"environment_vars": \[\]}, "type": "RebootRequired"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
      """
    When I run `pro system reboot-required` as non-root
    Then I will see the following on stdout:
      """
      no
      """
    When I apt install `libc6`
    And I run `pro api u.pro.security.status.reboot_required.v1` as non-root
    Then stdout matches regexp:
      """
      {"_schema_version": "v1", "data": {"attributes": {"livepatch_enabled": true, "livepatch_enabled_and_kernel_patched": true, "livepatch_state": "applied", "livepatch_support": "kernel-upgrade-required", "reboot_required": "yes", "reboot_required_packages": {"kernel_packages": \[\], "standard_packages": \["libc6"\]}}, "meta": {"environment_vars": \[\]}, "type": "RebootRequired"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
      """
    When I run `pro system reboot-required` as non-root
    Then I will see the following on stdout:
      """
      yes
      """
    When I reboot the machine
    And I run `pro system reboot-required` as non-root
    Then I will see the following on stdout:
      """
      no
      """
    When I apt install `linux-image-generic`
    And I run `pro api u.pro.security.status.reboot_required.v1` as non-root
    Then stdout matches regexp:
      """
      {"_schema_version": "v1", "data": {"attributes": {"livepatch_enabled": true, "livepatch_enabled_and_kernel_patched": true, "livepatch_state": "applied", "livepatch_support": "kernel-upgrade-required", "reboot_required": "yes", "reboot_required_packages": {"kernel_packages": \["linux-base"\], "standard_packages": \[\]}}, "meta": {"environment_vars": \[\]}, "type": "RebootRequired"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
      """
    When I run `pro system reboot-required` as non-root
    Then I will see the following on stdout:
      """
      yes
      """
    When I apt install `dbus`
    And I run `pro api u.pro.security.status.reboot_required.v1` with sudo
    Then stdout matches regexp:
      """
      {"_schema_version": "v1", "data": {"attributes": {"livepatch_enabled": true, "livepatch_enabled_and_kernel_patched": true, "livepatch_state": "applied", "livepatch_support": "kernel-upgrade-required", "reboot_required": "yes", "reboot_required_packages": {"kernel_packages": \["linux-base"\], "standard_packages": \["dbus"\]}}, "meta": {"environment_vars": \[\]}, "type": "RebootRequired"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
      """
    When I run `pro system reboot-required` as non-root
    Then I will see the following on stdout:
      """
      yes
      """

    Examples: ubuntu release
      | release | machine_type |
      | xenial  | lxd-vm       |

  @slow
  Scenario: Attached enable livepatch on a machine with fips active
    Given a `bionic` `lxd-vm` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then stdout matches regexp:
      """
      Updating Ubuntu Pro: ESM Infra package lists
      Ubuntu Pro: ESM Infra enabled
      Installing snapd snap
      Installing canonical-livepatch snap
      Canonical Livepatch enabled
      """
    When I run `pro disable livepatch` with sudo
    And I run `pro enable fips --assume-yes` with sudo
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Updating FIPS package lists
      Installing FIPS packages
      Updating standard Ubuntu package lists
      FIPS enabled
      A reboot is required to complete install.
      """
    When I append the following on uaclient config:
      """
      features:
        block_disable_on_enable: true
      """
    Then I verify that running `pro enable livepatch` `with sudo` exits `1`
    And I will see the following on stdout
      """
      One moment, checking your subscription first
      Cannot enable Livepatch when FIPS is enabled.
      """
    Then I verify that running `pro enable livepatch --format json --assume-yes` `with sudo` exits `1`
    And I will see the following on stdout
      """
      {"_schema_version": "0.1", "errors": [{"message": "Cannot enable Livepatch when FIPS is enabled.", "message_code": "livepatch-error-when-fips-enabled", "service": "livepatch", "type": "service"}], "failed_services": ["livepatch"], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
      """

  Scenario: Attached enable fips on a machine with livepatch active
    Given a `bionic` `lxd-vm` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then stdout matches regexp:
      """
      Updating Ubuntu Pro: ESM Infra package lists
      Ubuntu Pro: ESM Infra enabled
      Installing snapd snap
      Installing canonical-livepatch snap
      Canonical Livepatch enabled
      """
    When I append the following on uaclient config:
      """
      features:
        block_disable_on_enable: true
      """
    Then I verify that running `pro enable fips --assume-yes` `with sudo` exits `1`
    And I will see the following on stdout
      """
      One moment, checking your subscription first
      Cannot enable FIPS when Livepatch is enabled.
      """
    Then I verify that running `pro enable fips --assume-yes --format json` `with sudo` exits `1`
    And stdout is a json matching the `ua_operation` schema
    And I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [{"message": "Cannot enable FIPS when Livepatch is enabled.", "message_code": "incompatible-service-stops-enable", "service": "fips", "type": "service"}], "failed_services": ["fips"], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
      """

  @slow
  Scenario Outline: Attached enable fips on a machine with livepatch active
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then stdout matches regexp:
      """
      Updating Ubuntu Pro: ESM Infra package lists
      Ubuntu Pro: ESM Infra enabled
      """
    And stdout matches regexp:
      """
      Installing canonical-livepatch snap
      Canonical Livepatch enabled
      """
    When I run `pro enable fips --assume-yes` with sudo
    Then I will see the following on stdout
      """
      One moment, checking your subscription first
      Disabling incompatible service: Livepatch
      Updating FIPS package lists
      Installing FIPS packages
      Updating standard Ubuntu package lists
      FIPS enabled
      A reboot is required to complete install.
      """
    When I run `pro status --all` with sudo
    Then stdout matches regexp:
      """
      fips +yes +enabled
      """
    And stdout matches regexp:
      """
      livepatch +yes +n/a
      """

    Examples: ubuntu release
      | release | machine_type |
      | bionic  | lxd-vm       |
      | xenial  | lxd-vm       |

  @slow
  Scenario Outline: Attached enable fips on a machine with fips-updates active
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then stdout matches regexp:
      """
      Ubuntu Pro: ESM Infra enabled
      """
    And stdout matches regexp:
      """
      Installing canonical-livepatch snap
      Canonical Livepatch enabled
      """
    When I run `pro disable livepatch` with sudo
    And I run `pro enable fips-updates --assume-yes` with sudo
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Updating FIPS Updates package lists
      Installing FIPS Updates packages
      Updating standard Ubuntu package lists
      FIPS Updates enabled
      A reboot is required to complete install.
      """
    When I verify that running `pro enable fips --assume-yes` `with sudo` exits `1`
    Then I will see the following on stdout
      """
      One moment, checking your subscription first
      Cannot enable FIPS when FIPS Updates is enabled.
      """

    Examples: ubuntu release
      | release | machine_type |
      | bionic  | lxd-vm       |
      | xenial  | lxd-vm       |

  Scenario Outline: Attached enable ros on a machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then I verify that `ros` is disabled
    When I run `pro enable ros --assume-yes` with sudo
    Then I verify that `ros` is enabled
    And I verify that `esm-apps` is enabled
    And I verify that `esm-infra` is enabled
    When I verify that running `pro disable esm-apps` `with sudo` and stdin `N` exits `1`
    Then stdout matches regexp
      """
      ROS ESM Security Updates depends on Ubuntu Pro: ESM Apps.
      Disable ROS ESM Security Updates and proceed to disable Ubuntu Pro: ESM Apps\? \(y\/N\) Cannot disable Ubuntu Pro: ESM Apps when ROS ESM Security Updates is enabled.
      """
    When I run `pro disable esm-apps` `with sudo` and stdin `y`
    Then stdout matches regexp
      """
      ROS ESM Security Updates depends on Ubuntu Pro: ESM Apps.
      Disable ROS ESM Security Updates and proceed to disable Ubuntu Pro: ESM Apps\? \(y\/N\) Disabling dependent service: ROS ESM Security Updates
      Updating package lists
      """
    And I verify that `ros` is disabled
    And I verify that `esm-apps` is disabled
    When I verify that running `pro enable ros` `with sudo` and stdin `N` exits `1`
    Then stdout matches regexp
      """
      ROS ESM Security Updates cannot be enabled with Ubuntu Pro: ESM Apps disabled.
      Enable Ubuntu Pro: ESM Apps and proceed to enable ROS ESM Security Updates\? \(y\/N\) Cannot enable ROS ESM Security Updates when Ubuntu Pro: ESM Apps is disabled.
      """
    When I run `pro enable ros` `with sudo` and stdin `y`
    Then stdout matches regexp
      """
      One moment, checking your subscription first
      ROS ESM Security Updates cannot be enabled with Ubuntu Pro: ESM Apps disabled.
      Enable Ubuntu Pro: ESM Apps and proceed to enable ROS ESM Security Updates\? \(y\/N\) Enabling required service: Ubuntu Pro: ESM Apps
      Ubuntu Pro: ESM Apps enabled
      Updating ROS ESM Security Updates package lists
      ROS ESM Security Updates enabled
      """
    And I verify that `ros` is enabled
    And I verify that `esm-apps` is enabled
    And I verify that `esm-infra` is enabled
    When I run `apt-cache policy` as non-root
    Then apt-cache policy for the following url has priority `500`
      """
      <ros-security-source> amd64 Packages
      """
    When I apt install `python3-catkin-pkg`
    Then I verify that `python3-catkin-pkg` is installed from apt source `<ros-security-source>`
    When I run `pro enable ros-updates --assume-yes` with sudo
    Then I verify that `ros-updates` is enabled
    When I run `apt-cache policy` as non-root
    Then apt-cache policy for the following url has priority `500`
      """
      <ros-updates-source> amd64 Packages
      """
    When I apt install `python3-catkin-pkg`
    Then I verify that `python3-catkin-pkg` is installed from apt source `<ros-updates-source>`
    When I run `pro disable ros` `with sudo` and stdin `y`
    Then stdout matches regexp
      """
      ROS ESM All Updates depends on ROS ESM Security Updates.
      Disable ROS ESM All Updates and proceed to disable ROS ESM Security Updates\? \(y\/N\) Disabling dependent service: ROS ESM All Updates
      Updating package lists
      """
    And I verify that `ros-updates` is disabled
    When I run `pro enable ros-updates` `with sudo` and stdin `y`
    Then stdout matches regexp
      """
      One moment, checking your subscription first
      ROS ESM All Updates cannot be enabled with ROS ESM Security Updates disabled.
      Enable ROS ESM Security Updates and proceed to enable ROS ESM All Updates\? \(y\/N\) Enabling required service: ROS ESM Security Updates
      ROS ESM Security Updates enabled
      Updating ROS ESM All Updates package lists
      ROS ESM All Updates enabled
      """
    And I verify that `ros-updates` is enabled
    And I verify that `ros` is enabled
    When I run `pro disable ros-updates --assume-yes` with sudo
    And I run `pro disable ros --assume-yes` with sudo
    And I run `pro disable esm-apps --assume-yes` with sudo
    And I run `pro disable esm-infra --assume-yes` with sudo
    And I run `pro enable ros-updates --assume-yes` with sudo
    Then I verify that `ros-updates` is enabled
    And I verify that `ros` is enabled
    And I verify that `esm-apps` is enabled
    And I verify that `esm-infra` is enabled
    When I run `pro detach` `with sudo` and stdin `y`
    Then stdout matches regexp:
      """
      Updating package lists
      Updating package lists
      Updating package lists
      Updating package lists
      This machine is now detached.
      """
    And the machine is unattached

    Examples: ubuntu release
      | release | machine_type  | ros-security-source                                    | ros-updates-source                                            |
      | xenial  | lxd-container | https://esm.ubuntu.com/ros/ubuntu xenial-security/main | https://esm.ubuntu.com/ros-updates/ubuntu xenial-updates/main |
      | bionic  | lxd-container | https://esm.ubuntu.com/ros/ubuntu bionic-security/main | https://esm.ubuntu.com/ros-updates/ubuntu bionic-updates/main |
      | bionic  | wsl           | https://esm.ubuntu.com/ros/ubuntu bionic-security/main | https://esm.ubuntu.com/ros-updates/ubuntu bionic-updates/main |

  # Overall test for overrides; in the future, when many services
  # have overrides, we can consider removing this
  # esm-infra is a good choice because it doesn't already have
  # other overrides that would interfere with the test
  Scenario: Cloud overrides for a generic aws Focal instance
    Given a `focal` `aws.generic` machine with ubuntu-advantage-tools installed
    When I set the machine token overlay to the following yaml
      """
      machineTokenInfo:
        contractInfo:
          resourceEntitlements:
            - type: esm-infra
              overrides:
                - selector:
                    series: focal
                  directives:
                    additionalPackages:
                      - some-package-focal
                - selector:
                    cloud: aws
                  directives:
                    additionalPackages:
                      - some-package-aws
      """
    And I attach `contract_token` with sudo and options `--no-auto-enable`
    And I verify that running `pro enable esm-infra` `with sudo` exits `1`
    Then stdout matches regexp:
      """
      E: Unable to locate package some-package-aws
      """

  Scenario Outline: APT auth file is edited correctly on enable
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    When I run `wc -l /etc/apt/auth.conf.d/90ubuntu-advantage` with sudo
    Then I will see the following on stdout:
      """
      2 /etc/apt/auth.conf.d/90ubuntu-advantage
      """
    # simulate a scenario where the line should get replaced
    When I run `cp /etc/apt/auth.conf.d/90ubuntu-advantage /etc/apt/auth.conf.d/90ubuntu-advantage.backup` with sudo
    When I run `pro disable esm-infra` with sudo
    When I run `cp /etc/apt/auth.conf.d/90ubuntu-advantage.backup /etc/apt/auth.conf.d/90ubuntu-advantage` with sudo
    When I run `pro enable esm-infra` with sudo
    When I run `wc -l /etc/apt/auth.conf.d/90ubuntu-advantage` with sudo
    Then I will see the following on stdout:
      """
      2 /etc/apt/auth.conf.d/90ubuntu-advantage
      """
    When I run `pro enable cis` with sudo
    When I run `wc -l /etc/apt/auth.conf.d/90ubuntu-advantage` with sudo
    Then I will see the following on stdout:
      """
      3 /etc/apt/auth.conf.d/90ubuntu-advantage
      """

    Examples: ubuntu release
      | release | machine_type |
      | xenial  | aws.generic  |

  Scenario Outline: Attached enable esm-apps on a machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then I verify that `esm-apps` is enabled
    And I ensure apt update runs without errors
    When I run `apt-cache policy` as non-root
    Then apt-cache policy for the following url has priority `510`
      """
      https://esm.ubuntu.com/apps/ubuntu <release>-apps-updates/main amd64 Packages
      """
    And apt-cache policy for the following url has priority `510`
      """
      https://esm.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
      """
    And I ensure apt update runs without errors
    When I apt install `<apps-pkg>`
    And I run `apt-cache policy <apps-pkg>` as non-root
    Then stdout matches regexp:
      """
      Version table:
      \s*\*\*\* .* 510
      \s*510 https://esm.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
      """
    When I verify that running `pro enable esm-apps` `with sudo` exits `1`
    Then stdout matches regexp
      """
      One moment, checking your subscription first
      Ubuntu Pro: ESM Apps is already enabled.
      See: sudo pro status
      """

    Examples: ubuntu release
      | release | machine_type  | apps-pkg |
      | xenial  | lxd-container | jq       |
      | bionic  | lxd-container | bundler  |
      | focal   | lxd-container | ant      |

  Scenario Outline: Attached enable with corrupt lock
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I run `pro disable esm-infra --assume-yes` with sudo
    And I create the file `/var/lib/ubuntu-advantage/lock` with the following:
      """
      corrupted
      """
    Then I verify that running `pro enable esm-infra --assume-yes` `with sudo` exits `1`
    And stderr matches regexp:
      """
      There is a corrupted lock file in the system. To continue, please remove it
      from the system by running:

      \$ sudo rm /var/lib/ubuntu-advantage/lock
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
