@uses.config.contract_token
Feature: Livepatch

    @series.focal
    @uses.config.machine_type.lxd.vm
    Scenario Outline: Attached livepatch status shows warning when on unsupported kernel
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        livepatch +yes +Current kernel is not supported
        """
        Then stdout matches regexp:
        """
        Supported livepatch kernels are listed here: https://ubuntu.com/security/livepatch/docs/kernels
        """
        When I attach `contract_token` with sudo
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        livepatch +yes +warning +Current kernel is not supported
        """
        Then stdout matches regexp:
        """
        NOTICES
        The current kernel \(5.4.0-(\d+)-kvm, amd64\) is not supported by livepatch.
        Supported kernels are listed here: https://ubuntu.com/security/livepatch/docs/kernels
        Either switch to a supported kernel or `pro disable livepatch` to dismiss this warning.

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
        The current kernel \(5.4.0-(\d+)-kvm, amd64\) is not supported by livepatch.
        Supported kernels are listed here: https://ubuntu.com/security/livepatch/docs/kernels
        Either switch to a supported kernel or `pro disable livepatch` to dismiss this warning.

        """
        When I run `apt-get install linux-generic -y` with sudo
        When I run `DEBIAN_FRONTEND=noninteractive apt-get remove linux-image*-kvm -y` with sudo
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
        When I run `pro detach --assume-yes` with sudo
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        livepatch +yes +Canonical Livepatch service
        """
        Then stdout does not match regexp:
        """
        Supported livepatch kernels are listed here: https://ubuntu.com/security/livepatch/docs/kernels
        """
        Examples: ubuntu release
            | release |
            | focal   |
