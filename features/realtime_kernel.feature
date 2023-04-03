@uses.config.contract_token
Feature: Enable command behaviour when attached to an Ubuntu Pro subscription

    @series.jammy
    @uses.config.machine_type.lxd.container
    Scenario Outline: Enable Real-time kernel service in a container
        Given a `<release>` machine with ubuntu-advantage-tools installed
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
            """
        Examples: ubuntu release
            | release |
            | jammy   |

    @series.lts
    @uses.config.machine_type.lxd.vm
    Scenario Outline: Enable Real-time kernel service on unsupported release
        Given a `<release>` machine with ubuntu-advantage-tools installed
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
            """
        Examples: ubuntu release
            | release | version    | full_name       |
            | xenial  | 16.04 LTS  | Xenial Xerus    |
            | bionic  | 18.04 LTS  | Bionic Beaver   |
            | focal   | 20.04 LTS  | Focal Fossa     |

    @series.jammy
    @uses.config.machine_type.lxd.vm
    Scenario Outline: Enable Real-time kernel service
        Given a `<release>` machine with ubuntu-advantage-tools installed
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

            Do you want to continue\? \[ default = Yes \]: \(Y/n\) Updating package lists
            Installing Real-time kernel packages
            Real-time kernel enabled
            A reboot is required to complete install.
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
        When I verify that running `pro enable realtime-kernel` `with sudo` exits `1`
        Then stdout matches regexp
            """
            One moment, checking your subscription first
            Real-time kernel is already enabled.
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
        When I set the machine token overlay to the following yaml
        """
        machineTokenInfo:
          contractInfo:
            resourceEntitlements:
              - type: realtime-kernel
                overrides:
                  - directives:
                      additionalPackages:
                        - nvidia-prime
                    selector:
                      platform: nvidia-tegra
                  - directives:
                      additionalPackages:
                        - intel-pkg
                    selector:
                      platform: intel-iotg
        """
        And I run `pro enable realtime-kernel --variant nvidia-tegra` with sudo
        Then I will see the following on stdout:
        """
        One moment, checking your subscription first
        Updating package lists
        Installing Real-time Nvidia Tegra Kernel packages
        Real-time Nvidia Tegra Kernel enabled
        """
        When I run `pro status` as non-root
        Then stdout matches regexp:
        """
        realtime-kernel\* yes +enabled +Ubuntu kernel with PREEMPT_RT patches integrated

         \* This service has options, use pro status --all to see more details.
        """
         When I run `pro status --all` as non-root
         Then stdout matches regexp:
         """
         realtime-kernel  yes +enabled   +Ubuntu kernel with PREEMPT_RT patches integrated
         ├ generic        yes +disabled  +Generic version of the RT kernel \(default\)
         ├ nvidia-tegra   yes +enabled   +RT kernel optimized for NVidia Tegra platforms
         └ intel-iotg     yes +disabled  +RT kernel optimized for Intel IOTG platform
         """

        Examples: ubuntu release
            | release |
            | jammy   |

    @series.jammy
    @uses.config.machine_type.lxd.vm
    Scenario Outline: Enable Real-time kernel service access-only
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo and options `--no-auto-enable`
        When I run `pro enable realtime-kernel --beta --access-only` with sudo
        Then stdout matches regexp:
        """
        One moment, checking your subscription first
        Updating package lists
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
        When I run `apt-get install -y ubuntu-realtime` with sudo
        When I reboot the machine
        When I run `uname -r` as non-root
        Then stdout matches regexp:
        """
        realtime
        """
        Examples: ubuntu release
            | release |
            | jammy   |
