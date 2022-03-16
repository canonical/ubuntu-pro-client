@uses.config.contract_token
Feature: FIPS enablement in cloud based machines

    @series.lts
    @uses.config.machine_type.gcp.generic
    Scenario Outline: Attached enable of FIPS services in an ubuntu gcp vm
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua enable <fips_service> --assume-yes` `with sudo` exits `1`
        And stdout matches regexp:
        """
        Ubuntu <release_title> does not provide a GCP optimized FIPS kernel
        """

        Examples: fips
            | release | release_title | fips_service  |
            | xenial  | Xenial        | fips          |
            | xenial  | Xenial        | fips-updates  |

    @series.xenial
    @uses.config.machine_type.aws.generic
    @uses.config.machine_type.azure.generic
    Scenario Outline: FIPS unholds packages
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `DEBIAN_FRONTEND=noninteractive apt-get install -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -y openssh-client openssh-server strongswan` with sudo
        And I run `apt-mark hold openssh-client openssh-server strongswan` with sudo
        And I run `ua enable fips --assume-yes` with sudo
        Then I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-server-hmac` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client-hmac` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`
        When I run `ua disable fips --assume-yes` with sudo
        And I run `apt-mark unhold openssh-client openssh-server strongswan` with sudo
        Then I will see the following on stdout:
        """
        openssh-client was already not hold.
        openssh-server was already not hold.
        strongswan was already not hold.
        """
        When I reboot the `<release>` machine
        Then I verify that `openssh-server` installed version matches regexp `fips`
        And I verify that `openssh-client` installed version matches regexp `fips`
        And I verify that `strongswan` installed version matches regexp `fips`
        And I verify that `openssh-server-hmac` installed version matches regexp `fips`
        And I verify that `openssh-client-hmac` installed version matches regexp `fips`
        And I verify that `strongswan-hmac` installed version matches regexp `fips`

        Examples: ubuntu release
           | release | fips-apt-source                                |
           | xenial  | https://esm.ubuntu.com/fips/ubuntu xenial/main |


    @series.bionic
    @uses.config.machine_type.aws.generic
    @uses.config.machine_type.azure.generic
    @uses.config.machine_type.gcp.generic
    Scenario Outline: FIPS unholds packages
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `DEBIAN_FRONTEND=noninteractive apt-get install -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -y openssh-client openssh-server strongswan` with sudo
        And I run `apt-mark hold openssh-client openssh-server strongswan` with sudo
        And I run `ua enable fips --assume-yes` with sudo
        Then I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-server-hmac` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client-hmac` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`
        When I run `ua disable fips --assume-yes` with sudo
        And I run `apt-mark unhold openssh-client openssh-server strongswan` with sudo
        Then I will see the following on stdout:
        """
        openssh-client was already not hold.
        openssh-server was already not hold.
        strongswan was already not hold.
        """
        When I reboot the `<release>` machine
        Then I verify that `openssh-server` installed version matches regexp `fips`
        And I verify that `openssh-client` installed version matches regexp `fips`
        And I verify that `strongswan` installed version matches regexp `fips`
        And I verify that `openssh-server-hmac` installed version matches regexp `fips`
        And I verify that `openssh-client-hmac` installed version matches regexp `fips`
        And I verify that `strongswan-hmac` installed version matches regexp `fips`

        Examples: ubuntu release
           | release | fips-apt-source                                |
           | bionic  | https://esm.ubuntu.com/fips/ubuntu bionic/main |

    @series.focal
    @uses.config.machine_type.aws.generic
    @uses.config.machine_type.azure.generic
    @uses.config.machine_type.gcp.generic
    Scenario Outline: FIPS unholds packages
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `DEBIAN_FRONTEND=noninteractive apt-get install -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -y openssh-client openssh-server strongswan` with sudo
        And I run `apt-mark hold openssh-client openssh-server strongswan` with sudo
        And I run `ua enable fips --assume-yes` with sudo
        Then I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`
        When I run `ua disable fips --assume-yes` with sudo
        And I run `apt-mark unhold openssh-client openssh-server strongswan` with sudo
        Then I will see the following on stdout:
        """
        openssh-client was already not hold.
        openssh-server was already not hold.
        strongswan was already not hold.
        """
        When I reboot the `<release>` machine
        Then I verify that `openssh-server` installed version matches regexp `fips`
        And I verify that `openssh-client` installed version matches regexp `fips`
        And I verify that `strongswan` installed version matches regexp `fips`
        And I verify that `strongswan-hmac` installed version matches regexp `fips`

        Examples: ubuntu release
           | release | fips-apt-source                                |
           | focal   | https://esm.ubuntu.com/fips/ubuntu focal/main  |

    @slow
    @series.xenial
    @series.bionic
    @series.focal
    @uses.config.machine_type.azure.generic
    Scenario Outline: Enable FIPS in an ubuntu Azure vm
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua enable <fips-service> --assume-yes` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            Installing <fips-name> packages
            <fips-name> enabled
            A reboot is required to complete install
            """
        When I run `ua status --all` with sudo
        Then stdout matches regexp:
            """
            <fips-service> +yes                enabled
            """
        And I verify that running `apt update` `with sudo` exits `0`
        And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
        When I run `apt-cache policy <fips-package>` as non-root
        Then stdout does not match regexp:
        """
        .*Installed: \(none\)
        """
        When I reboot the `<release>` machine
        And  I run `uname -r` as non-root
        Then stdout matches regexp:
            """
            <fips-kernel>
            """
        When I run `cat /proc/sys/crypto/fips_enabled` with sudo
        Then I will see the following on stdout:
        """
        1
        """
        When I run `ua disable <fips-service> --assume-yes` with sudo
        Then stdout matches regexp:
        """
        Updating package lists
        """
        When I run `apt-cache policy <fips-package>` as non-root
        Then stdout matches regexp:
        """
        .*Installed: \(none\)
        """
        When I reboot the `<release>` machine
        And I run `ua status --all` with sudo
        Then stdout matches regexp:
            """
            <fips-service> +yes                disabled
            """

        Examples: ubuntu release
           | release | fips-name    | fips-service | fips-package      | fips-kernel  | fips-apt-source                                |
           | xenial  | FIPS         | fips         | ubuntu-fips       |  fips        | https://esm.ubuntu.com/fips/ubuntu xenial/main |
           | xenial  | FIPS Updates | fips-updates | ubuntu-fips       |  fips        | https://esm.ubuntu.com/fips/ubuntu xenial/main |
           | bionic  | FIPS         | fips         | ubuntu-azure-fips |  azure-fips  | https://esm.ubuntu.com/fips/ubuntu bionic/main |
           | bionic  | FIPS Updates | fips-updates | ubuntu-azure-fips |  azure-fips  | https://esm.ubuntu.com/fips/ubuntu bionic/main |
           | focal   | FIPS         | fips         | ubuntu-azure-fips |  azure-fips  | https://esm.ubuntu.com/fips/ubuntu focal/main  |
           | focal   | FIPS Updates | fips-updates | ubuntu-azure-fips |  azure-fips  | https://esm.ubuntu.com/fips/ubuntu focal/main  |

    @slow
    @series.xenial
    @uses.config.machine_type.aws.generic
    Scenario Outline: Attached FIPS in an ubuntu Xenial AWS vm
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua disable livepatch` with sudo
        And I run `DEBIAN_FRONTEND=noninteractive apt-get install -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -y openssh-client openssh-server strongswan` with sudo
        And I run `ua enable <fips-service> --assume-yes` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            Installing <fips-name> packages
            <fips-name> enabled
            A reboot is required to complete install
            """
        When I run `ua status --all` with sudo
        Then stdout matches regexp:
            """
            <fips-service> +yes                enabled
            """
        And I verify that running `apt update` `with sudo` exits `0`
        And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
        And I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-server-hmac` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client-hmac` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`
        When I run `apt-cache policy ubuntu-fips` as non-root
        Then stdout does not match regexp:
        """
        .*Installed: \(none\)
        """
        When I reboot the `<release>` machine
        And  I run `uname -r` as non-root
        Then stdout matches regexp:
            """
            fips
            """
        When I run `cat /proc/sys/crypto/fips_enabled` with sudo
        Then I will see the following on stdout:
        """
        1
        """
        When I run `ua disable <fips-service> --assume-yes` with sudo
        Then stdout matches regexp:
        """
        Updating package lists
        """
        When I run `apt-cache policy ubuntu-fips` as non-root
        Then stdout matches regexp:
        """
        .*Installed: \(none\)
        """
        When I reboot the `<release>` machine
        Then I verify that `openssh-server` installed version matches regexp `fips`
        And I verify that `openssh-client` installed version matches regexp `fips`
        And I verify that `strongswan` installed version matches regexp `fips`
        And I verify that `openssh-server-hmac` installed version matches regexp `fips`
        And I verify that `openssh-client-hmac` installed version matches regexp `fips`
        And I verify that `strongswan-hmac` installed version matches regexp `fips`
        When I run `apt-mark unhold openssh-client openssh-server strongswan` with sudo
        Then I will see the following on stdout:
        """
        openssh-client was already not hold.
        openssh-server was already not hold.
        strongswan was already not hold.
        """
        When I run `ua status --all` with sudo
        Then stdout matches regexp:
            """
            <fips-service> +yes                disabled
            """

        Examples: ubuntu release
           | release | fips-name    | fips-service |fips-apt-source                                |
           | xenial  | FIPS         | fips         |https://esm.ubuntu.com/fips/ubuntu xenial/main |

    @slow
    @series.bionic
    @series.focal
    @uses.config.machine_type.aws.generic
    Scenario Outline: Attached enable of FIPS in an ubuntu AWS vm
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua disable livepatch` with sudo
        And I run `ua enable <fips-service> --assume-yes` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            Installing <fips-name> packages
            <fips-name> enabled
            A reboot is required to complete install
            """
        When I run `ua status --all` with sudo
        Then stdout matches regexp:
            """
            <fips-service> +yes                enabled
            """
        And I verify that running `apt update` `with sudo` exits `0`
        And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
        When I run `apt-cache policy ubuntu-aws-fips` as non-root
        Then stdout does not match regexp:
        """
        .*Installed: \(none\)
        """
        When I reboot the `<release>` machine
        And  I run `uname -r` as non-root
        Then stdout matches regexp:
            """
            aws-fips
            """
        When I run `cat /proc/sys/crypto/fips_enabled` with sudo
        Then I will see the following on stdout:
        """
        1
        """
        When I run `ua disable <fips-service> --assume-yes` with sudo
        Then stdout matches regexp:
        """
        Updating package lists
        """
        When I run `apt-cache policy ubuntu-aws-fips` as non-root
        Then stdout matches regexp:
        """
        .*Installed: \(none\)
        """
        When I reboot the `<release>` machine
        And I run `ua status --all` with sudo
        Then stdout matches regexp:
            """
            <fips-service> +yes                disabled
            """

        Examples: ubuntu release
           | release | fips-name    | fips-service |fips-apt-source                                |
           | bionic  | FIPS         | fips         |https://esm.ubuntu.com/fips/ubuntu bionic/main |
           | bionic  | FIPS Updates | fips-updates |https://esm.ubuntu.com/fips/ubuntu bionic/main |
           | focal   | FIPS         | fips         |https://esm.ubuntu.com/fips/ubuntu focal/main  |
           | focal   | FIPS Updates | fips-updates |https://esm.ubuntu.com/fips/ubuntu focal/main  |

    @slow
    @series.bionic
    @series.focal
    @uses.config.machine_type.gcp.generic
    Scenario Outline: Attached enable of FIPS in an ubuntu GCP vm
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua enable <fips-service> --assume-yes` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            Installing <fips-name> packages
            <fips-name> enabled
            A reboot is required to complete install
            """
        When I run `ua status --all` with sudo
        Then stdout matches regexp:
            """
            <fips-service> +yes                enabled
            """
        And I verify that running `apt update` `with sudo` exits `0`
        And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
        When I run `apt-cache policy ubuntu-gcp-fips` as non-root
        Then stdout does not match regexp:
        """
        .*Installed: \(none\)
        """
        When I reboot the `<release>` machine
        And  I run `uname -r` as non-root
        Then stdout matches regexp:
            """
            gcp-fips
            """
        When I run `cat /proc/sys/crypto/fips_enabled` with sudo
        Then I will see the following on stdout:
        """
        1
        """
        When I run `ua disable <fips-service> --assume-yes` with sudo
        Then stdout matches regexp:
        """
        Updating package lists
        """
        When I run `apt-cache policy ubuntu-gcp-fips` as non-root
        Then stdout matches regexp:
        """
        .*Installed: \(none\)
        """
        When I reboot the `<release>` machine
        And I run `ua status --all` with sudo
        Then stdout matches regexp:
            """
            <fips-service> +yes                disabled
            """

        Examples: ubuntu release
           | release | fips-name    | fips-service |fips-apt-source                                |
           | bionic  | FIPS         | fips         |https://esm.ubuntu.com/fips/ubuntu bionic/main |
           | bionic  | FIPS Updates | fips-updates |https://esm.ubuntu.com/fips/ubuntu bionic/main |
           | focal   | FIPS         | fips         |https://esm.ubuntu.com/fips/ubuntu focal/main  |
           | focal   | FIPS Updates | fips-updates |https://esm.ubuntu.com/fips/ubuntu focal/main  |
