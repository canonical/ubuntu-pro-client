@uses.config.contract_token
Feature: Livepatch

  Scenario Outline: Attached disable of livepatch in a lxd vm
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then stdout matches regexp:
      """
      Enabling Livepatch
      Livepatch enabled
      """
    Then I verify that `esm-apps` is enabled
    And I verify that `esm-infra` is enabled
    And I verify that `livepatch` status is `<livepatch_status>`
    When I run `canonical-livepatch status` with sudo
    Then stdout matches regexp:
      """
      running: true
      """
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
      Could not enable Livepatch.
      """

    Examples: ubuntu release
      | release | machine_type | livepatch_status |
      | xenial  | lxd-vm       | warning          |
      | bionic  | lxd-vm       | enabled          |
      | noble   | lxd-vm       | enabled          |

  Scenario Outline: Unattached livepatch status shows warning when on unsupported kernel
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I change config key `livepatch_url` to use value `<livepatch_url>`
    Then I verify that no files exist matching `/home/ubuntu/.cache/ubuntu-pro/livepatch-kernel-support-cache.json`
    # This is needed because `apt update` creates this file before, and we need to make sure it is created correctly later
    When I delete the file `/run/ubuntu-advantage/livepatch-kernel-support-cache.json`
    When I run `pro status` as non-root
    Then I verify that files exist matching `/home/ubuntu/.cache/ubuntu-pro/livepatch-kernel-support-cache.json`
    Then I verify that no files exist matching `/run/ubuntu-advantage/livepatch-kernel-support-cache.json`
    When I run `pro status` with sudo
    Then stdout matches regexp:
      """
      livepatch +yes +Current kernel is not covered by livepatch
      """
    Then stdout contains substring:
      """
      Kernels covered by livepatch are listed here: https://ubuntu.com/security/livepatch/docs/kernels
      """
    Then I verify that files exist matching `/run/ubuntu-advantage/livepatch-kernel-support-cache.json`
    When I apt install `linux-generic`
    When I apt remove `linux-image*-kvm`
    When I run `update-grub` with sudo
    When I reboot the machine
    When I run `pro status` with sudo
    Then stdout matches regexp:
      """
      livepatch +yes +Canonical Livepatch service
      """
    Then stdout does not contain substring:
      """
      Kernels covered by livepatch are listed here: https://ubuntu.com/security/livepatch/docs/kernels
      """

    Examples: ubuntu release
      | release | machine_type | livepatch_url                           |
      | focal   | lxd-vm       | https://livepatch.canonical.com         |
      | focal   | lxd-vm       | https://livepatch.staging.canonical.com |

  Scenario Outline: Attached livepatch status shows warning when on unsupported kernel
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    When I run `pro status` with sudo
    Then stdout matches regexp:
      """
      livepatch +yes +warning +Current kernel is not covered by livepatch
      """
    Then stdout matches regexp:
      """
      NOTICES
      The current kernel \(5.4.0-(\d+)-kvm, x86_64\) is not covered by livepatch.
      Covered kernels are listed here: https://ubuntu.com/security/livepatch/docs/kernels
      Either switch to a covered kernel or `sudo pro disable livepatch` to dismiss this warning.
      """
    When I run `pro disable livepatch` with sudo
    When I run `pro status` with sudo
    Then stdout matches regexp:
      """
      livepatch +yes +disabled +Current kernel is not covered by livepatch
      """
    Then stdout does not match regexp:
      """
      NOTICES
      The current kernel \(5.4.0-(\d+)-kvm, x86_64\) is not covered by livepatch.
      Covered kernels are listed here: https://ubuntu.com/security/livepatch/docs/kernels
      Either switch to a covered kernel or `sudo pro disable livepatch` to dismiss this warning.
      """
    When I apt install `linux-generic`
    When I apt remove `linux-image*-kvm`
    When I run `update-grub` with sudo
    When I reboot the machine
    When I run `pro status` with sudo
    Then stdout matches regexp:
      """
      livepatch +yes +disabled +Canonical Livepatch service
      """
    When I run `pro enable livepatch` with sudo
    When I run `pro status` with sudo
    Then stdout matches regexp:
      """
      livepatch +yes +enabled +Canonical Livepatch service
      """

    Examples: ubuntu release
      | release | machine_type |
      | focal   | lxd-vm       |

  Scenario Outline: Attached livepatch status shows upgrade required when on an old kernel
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token_staging` with sudo
    When I apt install `linux-headers-<old_kernel_version> linux-image-<old_kernel_version>`
    When I apt remove `linux-image*-gcp`
    When I run `update-grub` with sudo
    When I reboot the machine
    When I run `uname -r` with sudo
    Then stdout contains substring:
      """
      <old_kernel_version>
      """
    And I verify that `livepatch` status is warning
    When I run `pro status` with sudo
    Then stdout contains substring:
      """
      NOTICES
      The running kernel has reached the end of its active livepatch window.
      Please upgrade the kernel with apt and reboot for continued livepatch coverage.
      """
    When I apt install `linux-headers-generic linux-image-generic`
    When I reboot the machine
    When I run `uname -r` with sudo
    Then stdout does not contain substring:
      """
      <old_kernel_version>
      """
    And I verify that `livepatch` is enabled
    Then stdout does not contain substring:
      """
      NOTICES
      The running kernel has reached the end of its active livepatch window.
      Please upgrade the kernel with apt and reboot for continued livepatch coverage.
      """

    Examples: ubuntu release
      | release | machine_type | old_kernel_version |
      | focal   | gcp.generic  | 5.4.0-28-generic   |

  Scenario Outline: Livepatch is not enabled by default and can't be enabled on interim releases
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro status --all` with sudo
    Then stdout matches regexp:
      """
      livepatch +no +Current kernel is not covered by livepatch
      """
    When I attach `contract_token` with sudo
    When I run `pro status --all` with sudo
    Then stdout matches regexp:
      """
      livepatch +yes +n/a +Canonical Livepatch service
      """
    When I verify that running `pro enable livepatch` `with sudo` exits `1`
    Then stdout contains substring:
      """
      Livepatch is not available for Ubuntu <pretty_name>.
      """
    When I run `pro status --all` with sudo
    Then stdout matches regexp:
      """
      livepatch +yes +n/a +Canonical Livepatch service
      """

    Examples: ubuntu release
      | release | machine_type | pretty_name           |
      | plucky  | lxd-vm       | 25.04 (Plucky Puffin) |

  Scenario Outline: Livepatch is supported on interim HWE kernel
    # This test is intended to ensure that an interim HWE kernel has the correct support status
    # It should be kept up to date so that it runs on the latest LTS and installs the latest
    # HWE kernel for that release.
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I apt install `linux-generic-hwe-<release_num>`
    When I apt remove `linux-image*-kvm`
    When I run `update-grub` with sudo
    When I reboot the machine
    When I attach `contract_token` with sudo
    When I run `pro status` with sudo
    Then I verify that `livepatch` is enabled

    Examples: ubuntu release
      | release | machine_type | release_num |
      | jammy   | lxd-vm       | 22.04       |

  Scenario Outline: snapd installed as a snap if necessary
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `snap list` with sudo
    Then stdout does not contain substring:
      """
      snapd
      """
    When I set the machine token overlay to the following yaml
      """
      machineTokenInfo:
        contractInfo:
          resourceEntitlements:
            - type: livepatch
              directives:
                requiredSnaps:
                  - name: core22
      """
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    And I run `pro enable livepatch` with sudo
    Then stdout contains substring:
      """
      Installing snapd snap
      """
    When I run `snap list` with sudo
    Then stdout contains substring:
      """
      snapd
      """
    And stdout contains substring:
      """
      core22
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
      Enabling Ubuntu Pro: ESM Infra
      Ubuntu Pro: ESM Infra enabled
      Enabling Livepatch
      Livepatch enabled
      """
    When I run `pro disable livepatch` with sudo
    And I run `pro enable fips --assume-yes` with sudo
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Configuring APT access to FIPS
      Updating FIPS package lists
      Updating standard Ubuntu package lists
      Installing FIPS packages
      FIPS enabled
      A reboot is required to complete install.
      """
    When I append the following on uaclient config:
      """
      features:
        block_disable_on_enable: true
      """
    Then I verify that running `pro enable livepatch` `with sudo` exits `1`
    And I will see the following on stdout:
      """
      One moment, checking your subscription first
      Cannot enable Livepatch when FIPS is enabled.
      Could not enable Livepatch.
      """
    Then I verify that running `pro enable livepatch --format json --assume-yes` `with sudo` exits `1`
    And API full output matches regexp:
      """
      {
        "_schema_version": "0.1",
        "errors": [
          {
            "additional_info": null,
            "message": "Cannot enable Livepatch when FIPS is enabled.",
            "message_code": "livepatch-error-when-fips-enabled",
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

  Scenario Outline: Attach works when snapd cannot be installed
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I apt remove `snapd`
    And I create the file `/etc/apt/preferences.d/no-snapd` with the following:
      """
      Package: snapd
      Pin: release o=*
      Pin-Priority: -10
      """
    And I apt update
    When I attempt to attach `contract_token` with sudo
    Then I will see the following on stderr:
      """
      Failed to enable default services, check: sudo pro status
      """
    And I verify that `livepatch` is disabled
    And I verify that running `pro enable livepatch` `with sudo` exits `1`
    And I will see the following on stdout:
      """
      One moment, checking your subscription first
      Installing Livepatch
      Installing snapd
      Updating standard Ubuntu package lists
      Failed to install snapd on the system
      Could not enable Livepatch.
      """

    Examples: ubuntu release
      | release | machine_type |
      | xenial  | lxd-vm       |
      | bionic  | lxd-vm       |

  Scenario Outline: Livepatch doesn't enable on wsl from a systemd service
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/lib/systemd/system/test.service` with the following:
      """
      [Unit]
      Description=test

      [Service]
      Type=oneshot
      ExecStart=/usr/bin/pro attach <contract_token>
      PrivateMounts=yes
      """
    When I replace `<contract_token>` in `/lib/systemd/system/test.service` with token `contract_token`
    When I run `systemctl start test.service` with sudo
    Then I verify that running `canonical-livepatch` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      sudo: canonical-livepatch: command not found
      """

    Examples: ubuntu release
      | release | machine_type |
      | jammy   | wsl          |
