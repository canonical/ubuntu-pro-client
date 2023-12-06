@uses.config.contract_token
Feature: FIPS enablement in lxd containers

    Scenario Outline: Attached enable of FIPS in an ubuntu lxd container
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I apt install `openssh-client openssh-server strongswan openssl <libssl> libgcrypt20`
        And I run `pro enable fips<updates>` `with sudo` and stdin `y`
        Then stdout matches regexp:
        """
        Warning: Enabling <fips-name> in a container.
                 This will install the FIPS packages but not the kernel.
                 This container must run on a host with <fips-name> enabled to be
                 compliant.
        Warning: This action can take some time and cannot be undone.
        """
        And stdout contains substring:
        """
        Updating <fips-name> package lists
        Installing <fips-name> packages
        Updating standard Ubuntu package lists
        <fips-name> enabled
        A reboot is required to complete install.
        Please run `apt upgrade` to ensure all FIPS packages are updated to the correct
        version.
        """
        And I verify that `fips<updates>` is enabled
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
        """
        FIPS support requires system reboot to complete configuration
        """
        And I verify that running `apt update` `with sudo` exits `0`
        And I verify that `openssh-server` is installed from apt source `https://esm.ubuntu.com/fips<updates>/ubuntu <release><updates>/main`
        And I verify that `openssh-client` is installed from apt source `https://esm.ubuntu.com/fips<updates>/ubuntu <release><updates>/main`
        And I verify that `strongswan` is installed from apt source `https://esm.ubuntu.com/fips<updates>/ubuntu <release><updates>/main`
        And I verify that `strongswan-hmac` is installed from apt source `https://esm.ubuntu.com/fips<updates>/ubuntu <release><updates>/main`
        And I verify that `openssl` is installed from apt source `https://esm.ubuntu.com/fips<updates>/ubuntu <release><updates>/main`
        And I verify that `<libssl>` is installed from apt source `https://esm.ubuntu.com/fips<updates>/ubuntu <release><updates>/main`
        And I verify that `<libssl>-hmac` is installed from apt source `https://esm.ubuntu.com/fips<updates>/ubuntu <release><updates>/main`
        And I verify that `<additional-fips-packages>` are installed from apt source `https://esm.ubuntu.com/fips<updates>/ubuntu <release><updates>/main`
        When I reboot the machine
        When I run `pro status --all` with sudo
        Then stdout does not match regexp:
        """
        FIPS support requires system reboot to complete configuration
        """
        When I run `pro disable fips<updates>` `with sudo` and stdin `y`
        Then stdout matches regexp:
        """
        This will disable the <fips-name> entitlement but the <fips-name> packages will remain installed.
        """
        And stdout matches regexp:
        """
        Updating package lists
        """
        And stdout does not match regexp:
        """
        A reboot is required to complete disable operation
        """
        And I verify that `fips<updates>` is disabled
        When I run `pro status --all` with sudo
        Then stdout does not match regexp:
        """
        Disabling <fips-name> requires system reboot to complete operation
        """
        When I run `apt-cache policy ubuntu-fips` as non-root
        Then stdout does not match regexp:
        """
        .*Installed: \(none\)
        """
        Then I verify that `openssh-server` installed version matches regexp `fips`
        And I verify that `openssh-client` installed version matches regexp `fips`
        And I verify that `strongswan` installed version matches regexp `fips`
        And I verify that `strongswan-hmac` installed version matches regexp `fips`
        And I verify that `openssl` installed version matches regexp `fips`
        And I verify that `<libssl>` installed version matches regexp `fips`
        And I verify that `<libssl>-hmac` installed version matches regexp `fips`
        And I verify that packages `<additional-fips-packages>` installed versions match regexp `fips`

        Examples: ubuntu release
           | release | machine_type  | fips-name    | updates  | libssl      | additional-fips-packages                                             |
           | xenial  | lxd-container | FIPS         |          | libssl1.0.0 | openssh-server-hmac openssh-client-hmac                              |
           | xenial  | lxd-container | FIPS Updates | -updates | libssl1.0.0 | openssh-server-hmac openssh-client-hmac                              |
           | bionic  | lxd-container | FIPS         |          | libssl1.1   | openssh-server-hmac openssh-client-hmac libgcrypt20 libgcrypt20-hmac |
           | bionic  | lxd-container | FIPS Updates | -updates | libssl1.1   | openssh-server-hmac openssh-client-hmac libgcrypt20 libgcrypt20-hmac |
           | focal   | lxd-container | FIPS         |          | libssl1.1   | libgcrypt20 libgcrypt20-hmac                                         |
           | focal   | lxd-container | FIPS Updates | -updates | libssl1.1   | libgcrypt20 libgcrypt20-hmac                                         |

    Scenario Outline: Try to enable FIPS after FIPS Updates in a lxd container
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that `fips-updates` is disabled
        And I verify that `fips` is disabled
        When I run `pro enable fips-updates --assume-yes` with sudo
        Then I verify that `fips-updates` is enabled
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
        """
        fips +yes +n/a
        """
        When I verify that running `pro enable fips --assume-yes` `with sudo` exits `1`
        Then stdout matches regexp:
        """
        Cannot enable FIPS when FIPS Updates is enabled.
        """
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
        """
        fips +yes +n/a
        """
        And I verify that `fips-updates` is enabled

        Examples: ubuntu release
           | release | machine_type  |
           | xenial  | lxd-container |
           | bionic  | lxd-container |
           | focal   | lxd-container |
