@uses.config.contract_token
Feature: Enable command behaviour when attached to an UA subscription

    @series.jammy
    @uses.config.machine_type.lxd.container
    Scenario Outline: Enable Realtime Kernel service in a container
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua enable realtime-kernel` `as non-root` exits `1`
        And I will see the following on stderr:
            """
            This command must be run as root (try using sudo).
            """
        When I run `ua enable realtime-kernel` with sudo
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            Cannot install Realtime Kernel on a container.
            """
        Examples: ubuntu release
            | release |
            | jammy   |

    @series.xenial
    @series.bionic
    @series.focal
    @uses.config.machine_type.lxd.vm
    Scenario Outline: Enable Realtime Kernel service on unsupported release
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua enable realtime-kernel` `as non-root` exits `1`
        And I will see the following on stderr:
            """
            This command must be run as root (try using sudo).
            """
        When I run `ua enable realtime-kernel` with sudo
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            Realtime Kernel is not available for Ubuntu <version> (<full_name>).
            """
        Examples: ubuntu release
            | release | version    | full_name     |
            | xenial  | 16.04 LTS  | Xenial Xerus  |
            | bionic  | 18.04 LTS  | Bionic Beaver |
            | focal   | 20.04 LTS  | Focal Fossa   |
            | impish  | 21.10      | Impish Indri  |

    @series.jammy
    @uses.config.machine_type.lxd.vm
    Scenario Outline: Enable Realtime Kernel service
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua enable realtime-kernel` `as non-root` exits `1`
        And I will see the following on stderr:
            """
            This command must be run as root (try using sudo).
            """
        When I run `ua enable realtime-kernel` with sudo
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            Updating package lists
            Installing Realtime Kernel packages
            Realtime Kernel enabled
            Visit https://ubuntu.com/realtime to learn how to use Realtime Kernel
            """
        When I run `apt-cache policy ubuntu-realtime-kernel` as non-root
        Then stdout does not match regexp:
        """
        .*Installed: \(none\)
        """
        And stdout matches regexp:
        """
        \s* 500 https://esm.ubuntu.com/realtime-kernel/ubuntu <release>/main amd64 Packages
        """
        When I verify that running `ua enable realtime-kernel` `with sudo` exits `1`
        Then stdout matches regexp
        """
        One moment, checking your subscription first
        Realtime Kernel is already enabled.
        See: sudo ua status
        """
        Examples: ubuntu release
            | release |
            | jammy   |
