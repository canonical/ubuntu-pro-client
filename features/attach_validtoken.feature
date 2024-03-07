@uses.config.contract_token
Feature: Command behaviour when attaching a machine to an Ubuntu Pro
  subscription using a valid token

  Scenario Outline: Attached command in a non-lts ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      <status_string>
      """
    And stdout matches regexp:
      """
      For a list of all Ubuntu Pro services, run 'pro status --all'
      """
    When I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      SERVICE       +ENTITLED +STATUS   +DESCRIPTION
      anbox-cloud   +yes      +n/a      +.*
      cc-eal        +yes      +n/a      +Common Criteria EAL2 Provisioning Packages
      cis           +yes      +n/a      +Security compliance and audit tools
      esm-apps      +yes      +n/a      +Expanded Security Maintenance for Applications
      esm-infra     +yes      +n/a      +Expanded Security Maintenance for Infrastructure
      fips          +yes      +n/a      +NIST-certified FIPS crypto packages
      fips-preview  +yes      +n/a      +.*
      fips-updates  +yes      +n/a      +FIPS compliant crypto packages with stable security updates
      landscape     +yes      +<landscape>      +Management and administration tool for Ubuntu
      livepatch     +yes      +n/a      +Canonical Livepatch service
      """
    And stdout does not match regexp:
      """
      For a list of all Ubuntu Pro services, run 'pro status --all'
      """

    Examples: ubuntu release
      | release | machine_type  | landscape | status_string                                                           |
      | mantic  | lxd-container | disabled  | landscape +yes +disabled +Management and administration tool for Ubuntu |

  Scenario Outline: Attach command in a ubuntu lxd container
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I apt install `update-motd`
    And I apt install `<downrev_pkg>`
    And I run `pro refresh messages` with sudo
    Then stdout matches regexp:
      """
      Successfully updated Ubuntu Pro related APT and MOTD messages.
      """
    When I run `update-motd` with sudo
    Then if `<release>` in `xenial` and stdout matches regexp:
      """
      \d+ update(s)? can be applied immediately.
      \d+ of these updates (is a|are) standard security update(s)?.
      """
    Then if `<release>` in `bionic` and stdout matches regexp:
      """
      \d+ update(s)? can be applied immediately.
      \d+ of these updates (is a|are) standard security update(s)?.
      """
    Then if `<release>` in `focal` and stdout matches regexp:
      """
      \d+ update(s)? can be applied immediately.
      """
    When I attach `contract_token` with sudo
    Then stdout matches regexp:
      """
      Ubuntu Pro: ESM Infra enabled
      """
    And stdout matches regexp:
      """
      This machine is now attached to
      """
    And stderr matches regexp:
      """
      Enabling default service esm-infra
      """
    Then I verify that `esm-infra` is enabled
    And I verify that `esm-apps` is enabled
    When I verify that running `pro attach contract_token` `with sudo` exits `2`
    Then stderr matches regexp:
      """
      This machine is already attached to '.+'
      To use a different subscription first run: sudo pro detach.
      """
    And I verify that `/var/lib/ubuntu-advantage/status.json` is world readable

    Examples: ubuntu release packages
      | release | machine_type  | downrev_pkg            | cc_status | cis_or_usg | cis      | fips     | livepatch_desc              |
      | xenial  | lxd-container | libkrad0=1.13.2+dfsg-5 | disabled  | cis        | disabled | disabled | Canonical Livepatch service |
      | bionic  | lxd-container | libkrad0=1.16-2build1  | disabled  | cis        | disabled | disabled | Canonical Livepatch service |
      | focal   | lxd-container | hello=2.10-2ubuntu2    | n/a       | usg        | disabled | disabled | Canonical Livepatch service |
      | jammy   | lxd-container | hello=2.10-2ubuntu4    | n/a       | usg        | n/a      | n/a      | Canonical Livepatch service |

  Scenario Outline: Attach command with attach config
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    # simplest happy path
    When I create the file `/tmp/attach.yaml` with the following
      """
      token: <contract_token>
      """
    When I replace `<contract_token>` in `/tmp/attach.yaml` with token `contract_token`
    When I run `pro attach --attach-config /tmp/attach.yaml` with sudo
    Then I verify that `esm-apps` is enabled
    And I verify that `esm-infra` is enabled
    And I verify that `<cis_or_usg>` is disabled
    When I run `pro detach --assume-yes` with sudo
    # don't allow both token on cli and config
    Then I verify that running `pro attach TOKEN --attach-config /tmp/attach.yaml` `with sudo` exits `1`
    Then stderr matches regexp:
      """
      Do not pass the TOKEN arg if you are using --attach-config.
      Include the token in the attach-config file instead.
      """
    # happy path with service overrides
    When I create the file `/tmp/attach.yaml` with the following
      """
      token: <contract_token>
      enable_services:
        - esm-apps
        - <cis_or_usg>
      """
    When I replace `<contract_token>` in `/tmp/attach.yaml` with token `contract_token`
    When I run `pro attach --attach-config /tmp/attach.yaml` with sudo
    Then I verify that `esm-apps` is enabled
    And I verify that `esm-infra` is disabled
    And I verify that `<cis_or_usg>` is enabled
    When I run `pro detach --assume-yes` with sudo
    # missing token
    When I create the file `/tmp/attach.yaml` with the following
      """
      enable_services:
        - esm-apps
        - <cis_or_usg>
      """
    Then I verify that running `pro attach --attach-config /tmp/attach.yaml` `with sudo` exits `1`
    Then stderr matches regexp:
      """
      Error while reading /tmp/attach.yaml:
      Got value with incorrect type for field "token":
      Expected value with type StringDataValue but got type: null
      """
    # other schema error
    When I create the file `/tmp/attach.yaml` with the following
      """
      token: <contract_token>
      enable_services: {cis: true}
      """
    When I replace `<contract_token>` in `/tmp/attach.yaml` with token `contract_token`
    Then I verify that running `pro attach --attach-config /tmp/attach.yaml` `with sudo` exits `1`
    Then stderr matches regexp:
      """
      Error while reading /tmp/attach.yaml:
      Got value with incorrect type for field "enable_services":
      Expected value with type list but got type: dict
      """
    # invalid service name
    When I create the file `/tmp/attach.yaml` with the following
      """
      token: <contract_token>
      enable_services:
        - esm-apps
        - nonexistent
        - nonexistent2
      """
    When I replace `<contract_token>` in `/tmp/attach.yaml` with token `contract_token`
    Then I verify that running `pro attach --attach-config /tmp/attach.yaml` `with sudo` exits `1`
    And stderr matches regexp:
      """
      Cannot enable unknown service 'nonexistent, nonexistent2'.
      """
    And I verify that `esm-apps` is enabled
    And I verify that `esm-infra` is disabled

    Examples: ubuntu
      | release | machine_type  | cis_or_usg |
      | xenial  | lxd-container | cis        |
      | bionic  | lxd-container | cis        |
      | focal   | lxd-container | usg        |

  Scenario Outline: Auto enable by default and attached disable of livepatch in a lxd vm
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then I verify that `esm-infra` is enabled
    And I verify that `esm-apps` is enabled
    And I verify that `livepatch` status is `<livepatch_status>`
    When I run `pro disable livepatch` with sudo
    Then I verify that running `canonical-livepatch status` `with sudo` exits `1`
    And stderr matches regexp:
      """
      Machine is not enabled. Please run 'sudo canonical-livepatch enable' with the
      token obtained from https://ubuntu.com/livepatch.
      """
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
      | focal   | lxd-vm       | enabled          |
      | jammy   | lxd-vm       | enabled          |

  Scenario Outline: Attach command in an generic cloud images
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then stdout matches regexp:
      """
      Ubuntu Pro: ESM Infra enabled
      """
    And stdout matches regexp:
      """
      This machine is now attached to
      """
    And stderr matches regexp:
      """
      Enabling default service esm-infra
      """
    And I verify that `esm-infra` is enabled

    Examples: ubuntu release livepatch status
      | release | machine_type  |
      | xenial  | aws.generic   |
      | xenial  | azure.generic |
      | xenial  | gcp.generic   |
      | bionic  | aws.generic   |
      | bionic  | azure.generic |
      | bionic  | gcp.generic   |
      | focal   | aws.generic   |
      | focal   | azure.generic |
      | focal   | gcp.generic   |
      | jammy   | aws.generic   |
      | jammy   | azure.generic |
      | jammy   | gcp.generic   |

  Scenario Outline: Attach command with json output
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I verify that running attach `as non-root` with json response exits `1`
    Then I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [{"message": "This command must be run as root (try using sudo).", "message_code": "nonroot-user", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
      """
    When I verify that running attach `with sudo` with json response exits `0`
    Then I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [], "failed_services": [], "needs_reboot": false, "processed_services": ["esm-apps", "esm-infra"], "result": "success", "warnings": []}
      """
    And I verify that `esm-infra` is enabled
    And I verify that `esm-apps` is enabled

    Examples: ubuntu release
      | release | machine_type  | cc-eal   |
      | xenial  | lxd-container | disabled |
      | bionic  | lxd-container | disabled |
      | focal   | lxd-container | n/a      |
      | jammy   | lxd-container | n/a      |

  Scenario Outline: Attach and Check for contract change in status checking
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then stdout matches regexp:
      """
      Ubuntu Pro: ESM Infra enabled
      """
    And stdout matches regexp:
      """
      This machine is now attached to
      """
    And I verify that `esm-infra` is enabled
    When I set the machine token overlay to the following yaml
      """
      machineTokenInfo:
        contractInfo:
          effectiveTo: 2000-01-02T03:04:05Z
      """
    And I delete the file `/var/lib/ubuntu-advantage/jobs-status.json`
    And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
    And I run `pro status` with sudo
    Then stdout matches regexp:
      """
      A change has been detected in your contract.
      Please run `sudo pro refresh`.
      """
    When I run `pro refresh contract` with sudo
    Then stdout matches regexp:
      """
      Successfully refreshed your subscription.
      """
    # remove machine token overlay
    When I change config key `features` to use value `{}`
    And I run `pro status` with sudo
    Then stdout does not match regexp:
      """
      A change has been detected in your contract.
      Please run `sudo pro refresh`.
      """

    Examples: ubuntu release livepatch status
      | release | machine_type |

  # removing until we add this feature back in a way that doesn't hammer the server
  # | xenial  | lxd-container |
  # | bionic  | lxd-container |
  # | focal   | lxd-container |
  Scenario Outline: Attach and Check for contract change in status checking
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/tmp/response-overlay.json` with the following:
      """
      {
          "https://contracts.canonical.com/v1/context/machines/token": [
          {
            "code": 200,
            "response": {
              "machineTokenInfo": {
                "contractInfo": {
                  "resourceEntitlements": [
                    {
                      "type": "esm-infra",
                      "directives": {
                        "aptURL": "test",
                        "suites": ["<release>"]
                      }
                    },
                    {
                      "type": "esm-apps",
                      "directives": {
                        "aptURL": "test",
                        "suites": ["<release>"]
                      }
                    }
                  ]
                }
              }
            }
         }]
      }
      """
    And I append the following on uaclient config:
      """
      features:
        serviceclient_url_responses: "/tmp/response-overlay.json"
      """
    And I verify that running `pro attach TOKEN` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      There is a problem with the resource directives provided by https://contracts.canonical.com
      These entitlements: esm-apps, esm-infra are sharing the following directives
       - APT url: test
       - Suite: <release>
      These directives need to be unique for every entitlement.
      """
    And the machine is unattached

    Examples: ubuntu release livepatch status
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
