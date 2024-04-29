@uses.config.contract_token
Feature: Enable command behaviour when attached to an Ubuntu Pro subscription

  Scenario Outline: Enable Real-time kernel service in a container
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    Then I verify that running `pro enable realtime-kernel` `as non-root` exits `1`
    And I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    Then I verify that running `pro enable realtime-kernel --beta` `with sudo` exits `1`
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Cannot install Real-time kernel on a container.
      Could not enable Real-time kernel.
      """

    Examples: ubuntu release
      | release | machine_type  |
      | jammy   | lxd-container |

  Scenario Outline: Enable Real-time kernel service on unsupported release
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    Then I verify that running `pro enable realtime-kernel` `as non-root` exits `1`
    And I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    Then I verify that running `pro enable realtime-kernel --beta` `with sudo` exits `1`
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Real-time kernel is not available for Ubuntu <version> (<full_name>).
      Could not enable Real-time kernel.
      """

    Examples: ubuntu release
      | release | machine_type | version   | full_name     |
      | xenial  | lxd-vm       | 16.04 LTS | Xenial Xerus  |
      | bionic  | lxd-vm       | 18.04 LTS | Bionic Beaver |
      | focal   | lxd-vm       | 20.04 LTS | Focal Fossa   |

  Scenario Outline: Enable Real-time kernel service
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    Then I verify that running `pro enable realtime-kernel` `as non-root` exits `1`
    And I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    When I run `pro enable realtime-kernel` `with sudo` and stdin `y`
    Then stdout matches regexp:
      """
      One moment, checking your subscription first
      The Real-time kernel is an Ubuntu kernel with PREEMPT_RT patches integrated.

      .*This will change your kernel. To revert to your original kernel, you will need
      to make the change manually..*

      Do you want to continue\? \[ default = Yes \]: \(Y/n\) Configuring APT access to Real-time kernel
      Updating Real-time kernel package lists
      Updating standard Ubuntu package lists
      Installing Real-time kernel packages
      Real-time kernel enabled
      A reboot is required to complete install\.
      """
    When I run `apt-cache policy ubuntu-realtime` as non-root
    Then stdout does not match regexp:
      """
      .*Installed: \(none\)
      """
    And stdout matches regexp:
      """
      \s* 500 https://esm.ubuntu.com/realtime/ubuntu <release>/main amd64 Packages
      """
    When I run `pro api u.pro.status.enabled_services.v1` as non-root
    Then stdout matches regexp:
      """
      {"_schema_version": "v1", "data": {"attributes": {"enabled_services": \[{"name": "realtime-kernel", "variant_enabled": true, "variant_name": "generic"}\]}, "meta": {"environment_vars": \[\]}, "type": "EnabledServices"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
      """
    When I verify that running `pro enable realtime-kernel` `with sudo` exits `1`
    Then stdout matches regexp
      """
      One moment, checking your subscription first
      Real-time kernel is already enabled - nothing to do.
      See: sudo pro status
      """
    When I reboot the machine
    When I run `uname -r` as non-root
    Then stdout matches regexp:
      """
      realtime
      """
    When I run `pro disable realtime-kernel` `with sudo` and stdin `y`
    Then stdout matches regexp:
      """
      This will remove the boot order preference for the Real-time kernel and
      disable updates to the Real-time kernel.

      This will NOT fully remove the kernel from your system.

      After this operation is complete you must:
        - Ensure a different kernel is installed and configured to boot
        - Reboot into that kernel
        - Fully remove the realtime kernel packages from your system
            - This might look something like `apt remove linux\*realtime`,
              but you must ensure this is correct before running it.
      """
    When I run `apt-cache policy ubuntu-realtime` as non-root
    Then stdout contains substring
      """
      Installed: (none)
      """
    When I verify that running `pro enable realtime-kernel --access-only --variant nvidia-tegra` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      Error: Cannot use --access-only together with --variant.
      """
    # Test one variant
    # We need to disable this job before adding the overlay, because we might
    # write the machine token to disk with the override content
    When I run `pro config set update_messaging_timer=0` with sudo
    And I run `pro enable realtime-kernel --assume-yes` with sudo
    And I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      realtime-kernel  yes +enabled   +Ubuntu kernel with PREEMPT_RT patches integrated
      ├ generic        yes +enabled   +Generic version of the RT kernel \(default\)
      └ intel-iotg     yes +disabled  +RT kernel optimized for Intel IOTG platform
      """
    When I run `pro api u.pro.status.enabled_services.v1` as non-root
    Then stdout matches regexp:
      """
      {"_schema_version": "v1", "data": {"attributes": {"enabled_services": \[{"name": "realtime-kernel", "variant_enabled": true, "variant_name": "generic"}\]}, "meta": {"environment_vars": \[\]}, "type": "EnabledServices"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
      """
    When I run `pro enable realtime-kernel --variant intel-iotg` `with sudo` and stdin `y\ny\n`
    Then stdout contains substring:
      """
      Real-time Intel IOTG Kernel cannot be enabled with Real-time kernel.
      Disable Real-time kernel and proceed to enable Real-time Intel IOTG Kernel? (y/N)
      """
    When I run `apt-cache policy ubuntu-intel-iot-realtime` as non-root
    Then stdout does not match regexp:
      """
      Installed: \(none\)
      """
    When I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      realtime-kernel  yes +enabled   +Ubuntu kernel with PREEMPT_RT patches integrated
      ├ generic        yes +disabled   +Generic version of the RT kernel \(default\)
      └ intel-iotg     yes +enabled  +RT kernel optimized for Intel IOTG platform
      """
    When I run `pro api u.pro.status.enabled_services.v1` as non-root
    Then stdout matches regexp:
      """
      {"_schema_version": "v1", "data": {"attributes": {"enabled_services": \[{"name": "realtime-kernel", "variant_enabled": true, "variant_name": "intel-iotg"}\]}, "meta": {"environment_vars": \[\]}, "type": "EnabledServices"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
      """
    When I reboot the machine
    And I run `uname -r` as non-root
    Then stdout matches regexp:
      """
      intel
      """
    When I run `pro enable realtime-kernel --variant generic` `with sudo` and stdin `y\ny\n`
    And I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      realtime-kernel  yes +enabled   +Ubuntu kernel with PREEMPT_RT patches integrated
      ├ generic        yes +enabled   +Generic version of the RT kernel \(default\)
      └ intel-iotg     yes +disabled  +RT kernel optimized for Intel IOTG platform
      """
    When I run `pro enable realtime-kernel --variant intel-iotg` `with sudo` and stdin `y\ny\n`
    And I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      realtime-kernel  yes +enabled   +Ubuntu kernel with PREEMPT_RT patches integrated
      ├ generic        yes +disabled   +Generic version of the RT kernel \(default\)
      └ intel-iotg     yes +enabled  +RT kernel optimized for Intel IOTG platform
      """
    When I verify that running `pro enable realtime-kernel` `with sudo` exits `1`
    Then stdout contains substring:
      """
      Real-time kernel is already enabled - nothing to do.
      """
    When I run `pro disable realtime-kernel --assume-yes` with sudo
    When I run `apt-cache policy ubuntu-intel-iot-realtime` as non-root
    Then stdout contains substring:
      """
      Installed: (none)
      """
    # Test multiple variants
    When I set the machine token overlay to the following yaml
      """
      machineTokenInfo:
        contractInfo:
          resourceEntitlements:
            - type: realtime-kernel
              overrides:
                - selector:
                    variant: nvidia-tegra
                  directives:
                    additionalPackages:
                      - nvidia-prime
                - selector:
                    variant: rpi
                  directives:
                    additionalPackages:
                      - raspi-config
      """
    When I run `pro enable realtime-kernel --variant nvidia-tegra` `with sudo` and stdin `y`
    Then stdout matches regexp:
      """
      One moment, checking your subscription first
      The Real-time kernel is an Ubuntu kernel with PREEMPT_RT patches integrated.

      .*This will change your kernel. To revert to your original kernel, you will need
      to make the change manually..*

      Do you want to continue\? \[ default = Yes \]: \(Y/n\) Configuring APT access to Real-time NVIDIA Tegra Kernel
      Updating Real-time NVIDIA Tegra Kernel package lists
      Updating standard Ubuntu package lists
      Installing Real-time NVIDIA Tegra Kernel packages
      Real-time NVIDIA Tegra Kernel enabled
      """
    When I run `pro status` as non-root
    Then stdout matches regexp:
      """
      realtime-kernel\* yes +enabled +Ubuntu kernel with PREEMPT_RT patches integrated
      usg +yes +disabled +Security compliance and audit tools

       \* Service has variants
      """
    Then stdout contains substring:
      """
      For a list of all Ubuntu Pro services and variants, run 'pro status --all'
      """
    When I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      realtime-kernel  yes +enabled   +Ubuntu kernel with PREEMPT_RT patches integrated
      ├ generic        yes +disabled  +Generic version of the RT kernel \(default\)
      ├ intel-iotg     yes +disabled  +RT kernel optimized for Intel IOTG platform
      ├ nvidia-tegra   yes +enabled   +RT kernel optimized for NVIDIA Tegra platform
      └ rpi            yes +disabled  +24.04 Real-time kernel optimised for Raspberry Pi
      """
    When I verify that running `pro enable realtime-kernel --variant intel-iotg` `with sudo` and stdin `N` exits `1`
    Then stdout matches regexp:
      """
      Real-time Intel IOTG Kernel cannot be enabled with Real-time NVIDIA Tegra Kernel.
      Disable Real-time NVIDIA Tegra Kernel and proceed to enable Real-time Intel IOTG Kernel\? \(y/N\)
      """
    And stdout matches regexp:
      """
      Cannot enable Real-time Intel IOTG Kernel when Real-time NVIDIA Tegra Kernel is enabled.
      """
    When I run `pro enable realtime-kernel --variant rpi --assume-yes` with sudo
    When I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      realtime-kernel  yes +enabled   +Ubuntu kernel with PREEMPT_RT patches integrated
      ├ generic        yes +disabled  +Generic version of the RT kernel \(default\)
      ├ intel-iotg     yes +disabled  +RT kernel optimized for Intel IOTG platform
      ├ nvidia-tegra   yes +disabled  +RT kernel optimized for NVIDIA Tegra platform
      └ rpi            yes +enabled   +24.04 Real-time kernel optimised for Raspberry Pi
      """
    When I run `pro help realtime-kernel` as non-root
    Then I will see the following on stdout:
      """
      Name:
      realtime-kernel

      Entitled:
      yes

      Status:
      enabled

      Help:
      The Real-time kernel is an Ubuntu kernel with PREEMPT_RT patches integrated. It
      services latency-dependent use cases by providing deterministic response times.
      The Real-time kernel meets stringent preemption specifications and is suitable
      for telco applications and dedicated devices in industrial automation and
      robotics. The Real-time kernel is currently incompatible with FIPS and
      Livepatch.

      Variants:

        * generic: Generic version of the RT kernel (default)
        * intel-iotg: RT kernel optimized for Intel IOTG platform
        * nvidia-tegra: RT kernel optimized for NVIDIA Tegra platform
        * rpi: 24.04 Real-time kernel optimised for Raspberry Pi
      """
    When I run `pro disable realtime-kernel` `with sudo` and stdin `y`
    Then stdout matches regexp:
      """
      This will remove the boot order preference for the Real-time kernel and
      disable updates to the Real-time kernel.

      This will NOT fully remove the kernel from your system.

      After this operation is complete you must:
        - Ensure a different kernel is installed and configured to boot
        - Reboot into that kernel
        - Fully remove the realtime kernel packages from your system
            - This might look something like `apt remove linux\*realtime`,
              but you must ensure this is correct before running it.
      """
    When I run `pro status` as non-root
    Then stdout matches regexp:
      """
      realtime-kernel\* +yes +disabled   +Ubuntu kernel with PREEMPT_RT patches integrated
      """
    When I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      realtime-kernel  yes +disabled   +Ubuntu kernel with PREEMPT_RT patches integrated
      ├ generic        yes +disabled  +Generic version of the RT kernel \(default\)
      ├ intel-iotg     yes +disabled  +RT kernel optimized for Intel IOTG platform
      ├ nvidia-tegra   yes +disabled  +RT kernel optimized for NVIDIA Tegra platform
      └ rpi            yes +disabled  +24.04 Real-time kernel optimised for Raspberry Pi
      """
    When I verify that running `pro enable realtime-kernel --variant nonexistent` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      could not find entitlement named "nonexistent"
      """
    When I run `pro detach --assume-yes` with sudo
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      realtime-kernel +yes +Ubuntu kernel with PREEMPT_RT patches integrated
      """
    When I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      realtime-kernel +yes +Ubuntu kernel with PREEMPT_RT patches integrated
      """
    And stdout does not match regexp:
      """
      nvidia-tegra
      """
    And stdout does not match regexp:
      """
      intel-iotg
      """

    Examples: ubuntu release
      | release | machine_type |
      | jammy   | lxd-vm       |

  Scenario Outline: Enable Real-time kernel service access-only
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    When I run `pro enable realtime-kernel --access-only` with sudo
    Then stdout matches regexp:
      """
      One moment, checking your subscription first
      Configuring APT access to Real-time kernel
      Updating Real-time kernel package lists
      Skipping installing packages: ubuntu-realtime
      Real-time kernel access enabled
      """
    Then stdout does not match regexp:
      """
      A reboot is required to complete install.
      """
    When I run `apt-cache policy ubuntu-realtime` as non-root
    Then stdout matches regexp:
      """
      .*Installed: \(none\)
      """
    And stdout matches regexp:
      """
      \s* 500 https://esm.ubuntu.com/realtime/ubuntu <release>/main amd64 Packages
      """
    When I apt install `ubuntu-realtime`
    When I reboot the machine
    When I run `uname -r` as non-root
    Then stdout matches regexp:
      """
      realtime
      """

    Examples: ubuntu release
      | release | machine_type |
      | jammy   | lxd-vm       |
