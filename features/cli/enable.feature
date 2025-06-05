@uses.config.contract_token
Feature: CLI enable command

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
      | noble   | lxd-container |

  @arm64
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
      Configuring APT access to Ubuntu Pro: ESM Infra
      Updating Ubuntu Pro: ESM Infra package lists
      Ubuntu Pro: ESM Infra enabled
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |

  Scenario Outline: Attached enable of different services using json format
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then I verify that running `pro enable foobar --format json` `as non-root` exits `1`
    And stdout is a json matching the `ua_operation` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [
          {
            "message": "json formatted response requires --assume-yes flag.",
            "message_code": "json-format-require-assume-yes",
            "service": null,
            "type": "system"
          }
        ],
        "failed_services": [],
        "needs_reboot": false,
        "processed_services": [],
        "result": "failure",
        "warnings": []
      }
      """
    Then I verify that running `pro enable foobar --format json` `with sudo` exits `1`
    And stdout is a json matching the `ua_operation` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [
          {
            "message": "json formatted response requires --assume-yes flag.",
            "message_code": "json-format-require-assume-yes",
            "service": null,
            "type": "system"
          }
        ],
        "failed_services": [],
        "needs_reboot": false,
        "processed_services": [],
        "result": "failure",
        "warnings": []
      }
      """
    Then I verify that running `pro enable foobar --format json --assume-yes` `as non-root` exits `1`
    And stdout is a json matching the `ua_operation` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [
          {
            "message": "This command must be run as root (try using sudo).",
            "message_code": "nonroot-user",
            "service": null,
            "type": "system"
          }
        ],
        "failed_services": [],
        "needs_reboot": false,
        "processed_services": [],
        "result": "failure",
        "warnings": []
      }
      """
    And I verify that running `pro enable foobar --format json --assume-yes` `with sudo` exits `1`
    And stdout is a json matching the `ua_operation` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [
          {
            "additional_info": {
              "invalid_service": "foobar",
              "operation": "enable",
              "service_msg": "Try <valid_services>"
            },
            "message": "Cannot enable unknown service 'foobar'.\nTry <valid_services>",
            "message_code": "invalid-service-or-failure",
            "service": null,
            "type": "system"
          }
        ],
        "failed_services": [
          "foobar"
        ],
        "needs_reboot": false,
        "processed_services": [],
        "result": "failure",
        "warnings": []
      }
      """
    And I verify that running `pro enable blah foobar --format json --assume-yes` `with sudo` exits `1`
    And stdout is a json matching the `ua_operation` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [
          {
            "additional_info": {
              "invalid_service": "blah, foobar",
              "operation": "enable",
              "service_msg": "Try <valid_services>"
            },
            "message": "Cannot enable unknown service 'blah, foobar'.\nTry <valid_services>",
            "message_code": "invalid-service-or-failure",
            "service": null,
            "type": "system"
          }
        ],
        "failed_services": [
          "blah",
          "foobar"
        ],
        "needs_reboot": false,
        "processed_services": [],
        "result": "failure",
        "warnings": []
      }
      """
    And I verify that running `pro enable esm-infra --format json --assume-yes` `with sudo` exits `1`
    And stdout is a json matching the `ua_operation` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [
          {
            "message": "Ubuntu Pro: ESM Infra is already enabled - nothing to do.\nSee: sudo pro status",
            "message_code": "service-already-enabled",
            "service": "esm-infra",
            "type": "service"
          }
        ],
        "failed_services": [
          "esm-infra"
        ],
        "needs_reboot": false,
        "processed_services": [],
        "result": "failure",
        "warnings": []
      }
      """
    When I run `pro disable esm-infra` with sudo
    And I run `pro enable esm-infra --format json --assume-yes` with sudo
    Then stdout is a json matching the `ua_operation` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [],
        "failed_services": [],
        "needs_reboot": false,
        "processed_services": [
          "esm-infra"
        ],
        "result": "success",
        "warnings": []
      }
      """
    When I run `pro disable esm-infra` with sudo
    And I verify that running `pro enable esm-infra foobar --format json --assume-yes` `with sudo` exits `1`
    Then stdout is a json matching the `ua_operation` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [
          {
            "additional_info": {
              "invalid_service": "foobar",
              "operation": "enable",
              "service_msg": "Try <valid_services>"
            },
            "message": "Cannot enable unknown service 'foobar'.\nTry <valid_services>",
            "message_code": "invalid-service-or-failure",
            "service": null,
            "type": "system"
          }
        ],
        "failed_services": [
          "foobar"
        ],
        "needs_reboot": false,
        "processed_services": [
          "esm-infra"
        ],
        "result": "failure",
        "warnings": []
      }
      """
    When I run `pro disable esm-infra esm-apps` with sudo
    And I run `pro enable esm-infra esm-apps --beta --format json --assume-yes` with sudo
    Then stdout is a json matching the `ua_operation` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [],
        "failed_services": [],
        "needs_reboot": false,
        "processed_services": [
          "esm-apps",
          "esm-infra"
        ],
        "result": "success",
        "warnings": []
      }
      """

    Examples: ubuntu release
      | release | machine_type  | valid_services                                                                                                                             |
      | xenial  | lxd-container | anbox-cloud, cc-eal, cis, esm-apps, esm-infra, fips, fips-preview,\nfips-updates, landscape, livepatch, realtime-kernel, ros, ros-updates. |
      | bionic  | lxd-container | anbox-cloud, cc-eal, cis, esm-apps, esm-infra, fips, fips-preview,\nfips-updates, landscape, livepatch, realtime-kernel, ros, ros-updates. |
      | focal   | lxd-container | anbox-cloud, cc-eal, esm-apps, esm-infra, fips, fips-preview, fips-updates,\nlandscape, livepatch, realtime-kernel, ros, ros-updates, usg. |
      | jammy   | lxd-container | anbox-cloud, cc-eal, esm-apps, esm-infra, fips, fips-preview, fips-updates,\nlandscape, livepatch, realtime-kernel, ros, ros-updates, usg. |
      | noble   | lxd-container | anbox-cloud, cc-eal, esm-apps, esm-infra, fips, fips-preview, fips-updates,\nlandscape, livepatch, realtime-kernel, ros, ros-updates, usg. |

  Scenario Outline: Attached enable of ESM services in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then I verify that `esm-apps` is enabled
    And I verify that `esm-infra` is enabled
    And I verify that running `pro enable foobar` `as non-root` exits `1`
    And I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    And I verify that running `pro enable foobar` `with sudo` exits `1`
    And stdout matches regexp:
      """
      One moment, checking your subscription first
      Cannot enable unknown service 'foobar'.
      <msg>
      """
    And I verify that running `pro enable blah foobar` `with sudo` exits `1`
    And stdout matches regexp:
      """
      One moment, checking your subscription first
      Cannot enable unknown service 'blah, foobar'.
      <msg>
      """
    When I verify that running `pro enable livepatch` `as non-root` exits `1`
    Then I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    When I verify that running `pro enable livepatch` `with sudo` exits `1`
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Cannot install Livepatch on a container.
      Could not enable Livepatch.
      """
    When I verify that running `pro enable esm-infra` `with sudo` exits `1`
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Ubuntu Pro: ESM Infra is already enabled - nothing to do.
      See: sudo pro status
      Could not enable Ubuntu Pro: ESM Infra.
      """
    When I run `apt-cache policy` with sudo
    Then apt-cache policy for the following url has priority `510`
      """
      https://esm.ubuntu.com/infra/ubuntu <release>-infra-updates/main amd64 Packages
      """
    And apt-cache policy for the following url has priority `510`
      """
      https://esm.ubuntu.com/infra/ubuntu <release>-infra-security/main amd64 Packages
      """
    And apt-cache policy for the following url has priority `510`
      """
      https://esm.ubuntu.com/apps/ubuntu <release>-apps-updates/main amd64 Packages
      """
    And apt-cache policy for the following url has priority `510`
      """
      https://esm.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
      """
    And I ensure apt update runs without errors
    When I apt install `<infra-pkg>`
    And I run `apt-cache policy <infra-pkg>` as non-root
    Then stdout matches regexp:
      """
      \s*510 https://esm.ubuntu.com/infra/ubuntu <release>-infra-security/main amd64 Packages
      """
    When I apt install `<apps-pkg>`
    And I run `apt-cache policy <apps-pkg>` as non-root
    Then stdout matches regexp:
      """
      \s*\*\*\* .* 510
      \s*510 https://esm.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
      """

    Examples: ubuntu release
      | release | machine_type  | infra-pkg | apps-pkg | msg                                                                                                                                            |
      | xenial  | lxd-container | libkrad0  | jq       | Try anbox-cloud, cc-eal, cis, esm-apps, esm-infra, fips, fips-preview,\nfips-updates, landscape, livepatch, realtime-kernel, ros, ros-updates. |
      | bionic  | lxd-container | libkrad0  | bundler  | Try anbox-cloud, cc-eal, cis, esm-apps, esm-infra, fips, fips-preview,\nfips-updates, landscape, livepatch, realtime-kernel, ros, ros-updates. |
      | focal   | lxd-container | hello     | ant      | Try anbox-cloud, cc-eal, esm-apps, esm-infra, fips, fips-preview, fips-updates,\nlandscape, livepatch, realtime-kernel, ros, ros-updates, usg. |

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
    And I verify that running `pro enable esm-apps` `with sudo` exits `1`
    And I will see the following on stdout:
      """
      One moment, checking your subscription first
      This subscription is not entitled to Ubuntu Pro: ESM Apps
      View your subscription at: https://ubuntu.com/pro/dashboard
      Could not enable Ubuntu Pro: ESM Apps.
      """

    Examples: not entitled services
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |

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
      6 /etc/apt/auth.conf.d/90ubuntu-advantage
      """
    # simulate a scenario where the line should get replaced
    When I run `cp /etc/apt/auth.conf.d/90ubuntu-advantage /etc/apt/auth.conf.d/90ubuntu-advantage.backup` with sudo
    When I run `pro disable esm-infra` with sudo
    When I run `cp /etc/apt/auth.conf.d/90ubuntu-advantage.backup /etc/apt/auth.conf.d/90ubuntu-advantage` with sudo
    When I run `pro enable esm-infra` with sudo
    When I run `wc -l /etc/apt/auth.conf.d/90ubuntu-advantage` with sudo
    Then I will see the following on stdout:
      """
      6 /etc/apt/auth.conf.d/90ubuntu-advantage
      """
    When I run `pro enable cis` with sudo
    When I run `wc -l /etc/apt/auth.conf.d/90ubuntu-advantage` with sudo
    Then I will see the following on stdout:
      """
      7 /etc/apt/auth.conf.d/90ubuntu-advantage
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |

  Scenario Outline: Attached enable with corrupt lock
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I run `pro disable esm-infra --assume-yes` with sudo
    And I create the file `/var/lib/ubuntu-advantage/lock` with the following:
      """
      corrupted
      """
    Then I verify that running `pro enable esm-infra --assume-yes` `with sudo` exits `1`
    And stdout matches regexp:
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
      | noble   | lxd-container |

  Scenario Outline: Unattached enable fails in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I verify that running `pro enable esm-infra` `as non-root` exits `1`
    Then I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    When I verify that running `pro enable esm-infra` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      Cannot enable services when unattached - nothing to do.
      To use 'esm-infra' you need an Ubuntu Pro subscription.
      Personal and community subscriptions are available at no charge.
      See https://ubuntu.com/pro
      """
    When I verify that running `pro enable esm-infra --format json --assume-yes` `with sudo` exits `1`
    Then stdout is a json matching the `ua_operation` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [
          {
            "additional_info": {
              "operation": "enable",
              "valid_service": "esm-infra"
            },
            "message": "Cannot enable services when unattached - nothing to do.\nTo use 'esm-infra' you need an Ubuntu Pro subscription.\nPersonal and community subscriptions are available at no charge.\nSee https://ubuntu.com/pro",
            "message_code": "valid-service-failure-unattached",
            "service": null,
            "type": "system"
          }
        ],
        "failed_services": [],
        "needs_reboot": false,
        "processed_services": [],
        "result": "failure",
        "warnings": []
      }
      """
    When I verify that running `pro enable unknown` `as non-root` exits `1`
    Then I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    When I verify that running `pro enable unknown` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      Cannot enable unknown service 'unknown'.
      """
    When I verify that running `pro enable unknown --format json --assume-yes` `with sudo` exits `1`
    Then stdout is a json matching the `ua_operation` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [
          {
            "additional_info": {
              "invalid_service": "unknown",
              "operation": "enable",
              "service_msg": ""
            },
            "message": "Cannot enable unknown service 'unknown'.\n",
            "message_code": "invalid-service-or-failure",
            "service": null,
            "type": "system"
          }
        ],
        "failed_services": [],
        "needs_reboot": false,
        "processed_services": [],
        "result": "failure",
        "warnings": []
      }
      """
    When I verify that running `pro enable esm-infra unknown` `as non-root` exits `1`
    Then I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    When I verify that running `pro enable esm-infra unknown` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      Cannot enable unknown service 'unknown'.

      Cannot enable services when unattached - nothing to do.
      To use 'esm-infra' you need an Ubuntu Pro subscription.
      Personal and community subscriptions are available at no charge.
      See https://ubuntu.com/pro
      """
    When I verify that running `pro enable esm-infra unknown --format json --assume-yes` `with sudo` exits `1`
    Then stdout is a json matching the `ua_operation` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [
          {
            "additional_info": {
              "invalid_service": "unknown",
              "operation": "enable",
              "service_msg": "",
              "valid_service": "esm-infra"
            },
            "message": "Cannot enable unknown service 'unknown'.\n\nCannot enable services when unattached - nothing to do.\nTo use 'esm-infra' you need an Ubuntu Pro subscription.\nPersonal and community subscriptions are available at no charge.\nSee https://ubuntu.com/pro",
            "message_code": "mixed-services-failure-unattached",
            "service": null,
            "type": "system"
          }
        ],
        "failed_services": [],
        "needs_reboot": false,
        "processed_services": [],
        "result": "failure",
        "warnings": []
      }
      """

    Examples: ubuntu release
      | release  | machine_type  |
      | xenial   | lxd-container |
      | bionic   | lxd-container |
      | bionic   | wsl           |
      | focal    | lxd-container |
      | focal    | wsl           |
      | jammy    | lxd-container |
      | jammy    | wsl           |
      | noble    | lxd-container |
      | oracular | lxd-container |
      | plucky   | lxd-container |
