Feature: CLI disable command

  @uses.config.contract_token
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
    When I verify that running `pro disable foobar --format json` `as non-root` exits `1`
    Then stdout is a json matching the `ua_operation` schema
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
    When I verify that running `pro disable foobar --format json` `with sudo` exits `1`
    Then stdout is a json matching the `ua_operation` schema
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
    When I verify that running `pro disable foobar --format json --assume-yes` `with sudo` exits `1`
    Then stdout is a json matching the `ua_operation` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [
          {
            "additional_info": {
              "invalid_service": "foobar",
              "operation": "disable",
              "service_msg": "<msg>"
            },
            "message": "Cannot disable unknown service 'foobar'.\n<msg>",
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
    When I verify that running `pro disable foobar` `with sudo` exits `1`
    Then stdout matches regexp:
      """
      Cannot disable unknown service 'foobar'.
      <msg>
      """
    When I verify that running `pro disable livepatch` `with sudo` exits `1`
    Then I will see the following on stdout:
      """
      Livepatch is not currently enabled - nothing to do.
      See: sudo pro status
      """
    When I verify that running `pro disable livepatch --format json --assume-yes` `with sudo` exits `1`
    Then stdout is a json matching the `ua_operation` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [
          {
            "message": "Livepatch is not currently enabled - nothing to do.\nSee: sudo pro status",
            "message_code": "service-already-disabled",
            "service": "livepatch",
            "type": "service"
          }
        ],
        "failed_services": [
          "livepatch"
        ],
        "needs_reboot": false,
        "processed_services": [],
        "result": "failure",
        "warnings": []
      }
      """
    When I verify that running `pro disable livepatch foobar` `as non-root` exits `1`
    Then stderr matches regexp:
      """
      This command must be run as root \(try using sudo\)
      """
    When I verify that running `pro disable livepatch foobar` `with sudo` exits `1`
    Then stdout matches regexp:
      """
      Livepatch is not currently enabled - nothing to do.
      See: sudo pro status
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
    When I run `pro enable esm-infra` with sudo
    And I verify that running `pro disable esm-infra esm-apps --format json --assume-yes` `with sudo` exits `0`
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
    When I run `pro enable esm-infra` with sudo
    Then I verify that running `pro disable esm-infra foobar --format json --assume-yes` `with sudo` exits `1`
    And stdout is a json matching the `ua_operation` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [
          {
            "additional_info": {
              "invalid_service": "foobar",
              "operation": "disable",
              "service_msg": "<msg>"
            },
            "message": "Cannot disable unknown service 'foobar'.\n<msg>",
            "message_code": "invalid-service-or-failure",
            "service": null,
            "type": "system"
          }
        ],
        "failed_services": [],
        "needs_reboot": false,
        "processed_services": [
          "esm-infra"
        ],
        "result": "failure",
        "warnings": []
      }
      """

    Examples: ubuntu release
      | release | machine_type  | msg                                                                                                                                            |
      | xenial  | lxd-container | Try anbox-cloud, cc-eal, cis, esm-apps, esm-infra, fips, fips-preview,\nfips-updates, landscape, livepatch, realtime-kernel, ros, ros-updates. |
      | bionic  | lxd-container | Try anbox-cloud, cc-eal, cis, esm-apps, esm-infra, fips, fips-preview,\nfips-updates, landscape, livepatch, realtime-kernel, ros, ros-updates. |
      | focal   | lxd-container | Try anbox-cloud, cc-eal, esm-apps, esm-infra, fips, fips-preview, fips-updates,\nlandscape, livepatch, realtime-kernel, ros, ros-updates, usg. |
      | jammy   | lxd-container | Try anbox-cloud, cc-eal, esm-apps, esm-infra, fips, fips-preview, fips-updates,\nlandscape, livepatch, realtime-kernel, ros, ros-updates, usg. |
      | noble   | lxd-container | Try anbox-cloud, cc-eal, esm-apps, esm-infra, fips, fips-preview, fips-updates,\nlandscape, livepatch, realtime-kernel, ros, ros-updates, usg. |

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
      | noble   | lxd-container |

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
      | bionic  | wsl           | bionic-updates   |
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
      | noble   | lxd-vm       |

  @slow
  Scenario Outline: Disable and purge fips
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I apt update
    And I run `pro enable <fips-service> --assume-yes` with sudo
    And I reboot the machine
    Then I verify that `<fips-service>` is enabled
    When I run `uname -r` as non-root
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
    When I run `uname -r` as non-root
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

  Scenario Outline: Unattached disable fails in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I verify that running `pro disable esm-infra` `as non-root` exits `1`
    Then I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    When I verify that running `pro disable esm-infra` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      Cannot disable services when unattached - nothing to do.
      To use 'esm-infra' you need an Ubuntu Pro subscription.
      Personal and community subscriptions are available at no charge.
      See https://ubuntu.com/pro
      """
    When I verify that running `pro disable esm-infra --format json --assume-yes` `with sudo` exits `1`
    Then stdout is a json matching the `ua_operation` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [
          {
            "additional_info": {
              "operation": "disable",
              "valid_service": "esm-infra"
            },
            "message": "Cannot disable services when unattached - nothing to do.\nTo use 'esm-infra' you need an Ubuntu Pro subscription.\nPersonal and community subscriptions are available at no charge.\nSee https://ubuntu.com/pro",
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
    When I verify that running `pro disable unknown` `as non-root` exits `1`
    Then I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    When I verify that running `pro disable unknown` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      Cannot disable unknown service 'unknown'.
      """
    When I verify that running `pro disable unknown --format json --assume-yes` `with sudo` exits `1`
    Then stdout is a json matching the `ua_operation` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [
          {
            "additional_info": {
              "invalid_service": "unknown",
              "operation": "disable",
              "service_msg": ""
            },
            "message": "Cannot disable unknown service 'unknown'.\n",
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
    When I verify that running `pro disable esm-infra unknown` `as non-root` exits `1`
    Then I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    When I verify that running `pro disable esm-infra unknown` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      Cannot disable unknown service 'unknown'.

      Cannot disable services when unattached - nothing to do.
      To use 'esm-infra' you need an Ubuntu Pro subscription.
      Personal and community subscriptions are available at no charge.
      See https://ubuntu.com/pro
      """
    When I verify that running `pro disable esm-infra unknown --format json --assume-yes` `with sudo` exits `1`
    Then stdout is a json matching the `ua_operation` schema
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [
          {
            "additional_info": {
              "invalid_service": "unknown",
              "operation": "disable",
              "service_msg": "",
              "valid_service": "esm-infra"
            },
            "message": "Cannot disable unknown service 'unknown'.\n\nCannot disable services when unattached - nothing to do.\nTo use 'esm-infra' you need an Ubuntu Pro subscription.\nPersonal and community subscriptions are available at no charge.\nSee https://ubuntu.com/pro",
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
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | bionic  | wsl           |
      | focal   | lxd-container |
      | focal   | wsl           |
      | jammy   | lxd-container |
      | jammy   | wsl           |
      | mantic  | lxd-container |
      | noble   | lxd-container |
