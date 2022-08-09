
@uses.config.contract_token
Feature: FIPS enablement in lxd containers

    @series.xenial
    @series.bionic
    @series.focal
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached enable of FIPS in an ubuntu lxd container
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `DEBIAN_FRONTEND=noninteractive apt-get install -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -y openssh-client openssh-server strongswan openssl <libssl> libgcrypt20` with sudo, retrying exit [100]
        And I run `pro enable fips<updates>` `with sudo` and stdin `y`
        Then stdout matches regexp:
            """
            Warning: Enabling <fips-name> in a container.
                     This will install the FIPS packages but not the kernel.
                     This container must run on a host with <fips-name> enabled to be
                     compliant.
            Warning: This action can take some time and cannot be undone.
            """
        And stdout matches regexp:
            """
            Updating package lists
            Installing <fips-name> packages
            <fips-name> enabled
            A reboot is required to complete install.
            Please run `apt upgrade` to ensure all FIPS packages are updated to the correct
            version.
            """
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
            """
            fips<updates> +yes                enabled
            """
        And stdout matches regexp:
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
            This will disable the FIPS entitlement but the FIPS packages will remain installed.
            """
        And stdout matches regexp:
            """
            Updating package lists
            """
        And stdout does not match regexp:
            """
            A reboot is required to complete disable operation
            """
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
            """
            fips<updates> +yes                disabled
            """
        Then stdout does not match regexp:
            """
            Disabling FIPS requires system reboot to complete operation
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
           | release | fips-name    | updates  | libssl      | additional-fips-packages                                             |
           | xenial  | FIPS         |          | libssl1.0.0 | openssh-server-hmac openssh-client-hmac                              |
           | xenial  | FIPS Updates | -updates | libssl1.0.0 | openssh-server-hmac openssh-client-hmac                              |
           | bionic  | FIPS         |          | libssl1.1   | openssh-server-hmac openssh-client-hmac libgcrypt20 libgcrypt20-hmac |
           | bionic  | FIPS Updates | -updates | libssl1.1   | openssh-server-hmac openssh-client-hmac libgcrypt20 libgcrypt20-hmac |
           | focal   | FIPS         |          | libssl1.1   | libgcrypt20 libgcrypt20-hmac                                         |
           | focal   | FIPS Updates | -updates | libssl1.1   | libgcrypt20 libgcrypt20-hmac                                         |

    @series.xenial
    @series.bionic
    @series.focal
    @uses.config.machine_type.lxd.container
    Scenario Outline: Try to enable FIPS after FIPS Updates in a lxd container
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
            """
            fips-updates +yes +disabled
            """
        And stdout matches regexp:
            """
            fips +yes +disabled
            """
        When I run `pro enable fips-updates --assume-yes` with sudo
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
            """
            fips-updates +yes +enabled
            """
        And stdout matches regexp:
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
            fips-updates +yes +enabled
            """
        And stdout matches regexp:
            """
            fips +yes +n/a
            """
        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
