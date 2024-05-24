@uses.config.contract_token
Feature: Livepatch

  Scenario Outline: Livepatch is enabled by default
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then I verify that `livepatch` is enabled

    Examples: ubuntu release
      | release | machine_type |
      | noble   | lxd-vm       |

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
      livepatch +yes +Current kernel is not supported
      """
    Then stdout contains substring:
      """
      Supported livepatch kernels are listed here: https://ubuntu.com/security/livepatch/docs/kernels
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
      Supported livepatch kernels are listed here: https://ubuntu.com/security/livepatch/docs/kernels
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
      livepatch +yes +warning +Current kernel is not supported
      """
    Then stdout matches regexp:
      """
      NOTICES
      The current kernel \(5.4.0-(\d+)-kvm, x86_64\) is not supported by livepatch.
      Supported kernels are listed here: https://ubuntu.com/security/livepatch/docs/kernels
      Either switch to a supported kernel or `sudo pro disable livepatch` to dismiss this warning.
      """
    When I run `pro disable livepatch` with sudo
    When I run `pro status` with sudo
    Then stdout matches regexp:
      """
      livepatch +yes +disabled +Current kernel is not supported
      """
    Then stdout does not match regexp:
      """
      NOTICES
      The current kernel \(5.4.0-(\d+)-kvm, x86_64\) is not supported by livepatch.
      Supported kernels are listed here: https://ubuntu.com/security/livepatch/docs/kernels
      Either switch to a supported kernel or `sudo pro disable livepatch` to dismiss this warning.
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
      Please upgrade the kernel with apt and reboot for continued livepatch support.
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
      Please upgrade the kernel with apt and reboot for continued livepatch support.
      """

    Examples: ubuntu release
      | release | machine_type | old_kernel_version |
      | focal   | gcp.generic  | 5.4.0-28-generic   |

  Scenario Outline: Livepatch is not enabled by default and can't be enabled on interim releases
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro status --all` with sudo
    Then stdout matches regexp:
      """
      livepatch +no +Current kernel is not supported
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
      | release | machine_type | pretty_name             |
      | mantic  | lxd-vm       | 23.10 (Mantic Minotaur) |

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
