@uses.config.contract_token
Feature: FIPS enablement in lxd VMs

    @slow
    @series.xenial
    @series.bionic
    @uses.config.machine_type.lxd-vm
    Scenario Outline: Attached enable of FIPS in an ubuntu lxd vm
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        When I run `pro status --format json` with sudo
        Then stdout contains substring
        """
        {"available": "yes", "blocked_by": [{"name": "livepatch", "reason": "Livepatch cannot be enabled while running the official FIPS certified kernel. If you would like a FIPS compliant kernel with additional bug fixes and security updates, you can use the FIPS Updates service with Livepatch.", "reason_code": "livepatch-invalidates-fips"}], "description": "NIST-certified core packages", "description_override": null, "entitled": "yes", "name": "fips", "status": "disabled", "status_details": "FIPS is not configured", "warning": null}
        """
        When I run `pro disable livepatch` with sudo
        And I run `DEBIAN_FRONTEND=noninteractive apt-get install -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -y openssh-client openssh-server strongswan` with sudo, retrying exit [100]
        And I run `apt-mark hold openssh-client openssh-server strongswan` with sudo
        And I run `pro enable <fips-service>` `with sudo` and stdin `y`
        Then stdout matches regexp:
            """
            This will install the FIPS packages. The Livepatch service will be unavailable.
            Warning: This action can take some time and cannot be undone.
            """
        And stdout matches regexp:
            """
            Updating package lists
            Installing <fips-name> packages
            <fips-name> enabled
            A reboot is required to complete install
            """
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
            """
            <fips-service> +yes                enabled
            """
        And stdout matches regexp:
            """
            FIPS support requires system reboot to complete configuration
            """
        And I verify that running `apt update` `with sudo` exits `0`
        And I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-server-hmac` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client-hmac` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`
        When I run `pro status --format json --all` with sudo
        Then stdout contains substring:
        """
        {"available": "no", "blocked_by": [{"name": "fips", "reason": "Livepatch cannot be enabled while running the official FIPS certified kernel. If you would like a FIPS compliant kernel with additional bug fixes and security updates, you can use the FIPS Updates service with Livepatch.", "reason_code": "livepatch-invalidates-fips"}], "description": "Canonical Livepatch service", "description_override": null, "entitled": "yes", "name": "livepatch", "status": "n/a", "status_details": "Cannot enable Livepatch when FIPS is enabled.", "warning": null}
        """
        When I reboot the machine
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
        When I run `pro status --all` with sudo
        Then stdout does not match regexp:
        """
        FIPS support requires system reboot to complete configuration
        """
        When I run `pro disable <fips-service>` `with sudo` and stdin `y`
        Then stdout matches regexp:
        """
        This will disable the FIPS entitlement but the FIPS packages will remain installed.
        """
        And stdout matches regexp:
        """
        Updating package lists
        A reboot is required to complete disable operation
        """
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
        """
        Disabling FIPS requires system reboot to complete operation
        """
        When I run `apt-cache policy ubuntu-fips` as non-root
        Then stdout matches regexp:
        """
        .*Installed: \(none\)
        """
        When I reboot the machine
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
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
        """
        <fips-service> +yes                disabled
        """
        Then stdout does not match regexp:
        """
        Disabling FIPS requires system reboot to complete operation
        """
        When I run `pro enable <fips-service> --assume-yes --format json --assume-yes` with sudo
        Then stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
        """
        {"_schema_version": "0.1", "errors": [], "failed_services": [], "needs_reboot": true, "processed_services": ["<fips-service>"], "result": "success", "warnings": []}
        """
        When I reboot the machine
        And I run `pro disable <fips-service> --assume-yes --format json` with sudo
        Then stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
        """
        {"_schema_version": "0.1", "errors": [], "failed_services": [], "needs_reboot": true, "processed_services": ["<fips-service>"], "result": "success", "warnings": []}
        """
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
        """
        <fips-service> +yes                disabled
        """

        Examples: ubuntu release
           | release | fips-name    | fips-service |fips-apt-source                                |
           | xenial  | FIPS         | fips         |https://esm.ubuntu.com/fips/ubuntu xenial/main |
           | bionic  | FIPS         | fips         |https://esm.ubuntu.com/fips/ubuntu bionic/main |

    @slow
    @series.xenial
    @series.bionic
    @uses.config.machine_type.lxd-vm
    Scenario Outline: Attached enable of FIPS-updates in an ubuntu lxd vm
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `pro disable livepatch` with sudo
        And I run `DEBIAN_FRONTEND=noninteractive apt-get install -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -y openssh-client openssh-server strongswan` with sudo, retrying exit [100]
        When I run `pro enable <fips-service>` `with sudo` and stdin `y`
        Then stdout matches regexp:
            """
            This will install the FIPS packages including security updates.
            Warning: This action can take some time and cannot be undone.
            """
        And stdout matches regexp:
            """
            Updating package lists
            Installing <fips-name> packages
            <fips-name> enabled
            A reboot is required to complete install
            """
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
            """
            <fips-service> +yes                enabled
            """
        And I verify that running `apt update` `with sudo` exits `0`
        And I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-server-hmac` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client-hmac` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`
        When I run `pro status --all --format json` with sudo
        Then stdout contains substring:
        """
        {"available": "no", "blocked_by": [{"name": "fips-updates", "reason": "FIPS cannot be enabled if FIPS Updates has ever been enabled because FIPS Updates installs security patches that aren't officially certified.", "reason_code": "fips-updates-invalidates-fips"}], "description": "NIST-certified core packages", "description_override": null, "entitled": "yes", "name": "fips", "status": "n/a", "status_details": "Cannot enable FIPS when FIPS Updates is enabled.", "warning": null}
        """

        When I reboot the machine
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
        When I run `pro disable <fips-service>` `with sudo` and stdin `y`
        Then stdout matches regexp:
            """
            This will disable the FIPS entitlement but the FIPS packages will remain installed.
            """
        And stdout matches regexp:
            """
            Updating package lists
            A reboot is required to complete disable operation
            """
        When I reboot the machine
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
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
            """
            <fips-service> +yes                disabled
            """
        When I verify that running `pro enable fips --assume-yes` `with sudo` exits `1`
        Then stdout matches regexp:
            """
            Cannot enable FIPS because FIPS Updates was once enabled.
            """
        And I verify that files exist matching `/var/lib/ubuntu-advantage/services-once-enabled`

        When I run `pro enable <fips-service> --assume-yes` with sudo
        When I reboot the machine
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
            """
            <fips-service> +yes +enabled
            """
        Then stdout matches regexp:
            """
            livepatch +yes +disabled
            """
        When I run `pro enable livepatch --assume-yes` with sudo
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
            """
            <fips-service> +yes +enabled
            """
        Then stdout matches regexp:
            """
            livepatch +yes +enabled
            """
        When I run `pro status --all --format json` with sudo
        Then stdout contains substring:
        """
        {"available": "no", "blocked_by": [{"name": "livepatch", "reason": "Livepatch cannot be enabled while running the official FIPS certified kernel. If you would like a FIPS compliant kernel with additional bug fixes and security updates, you can use the FIPS Updates service with Livepatch.", "reason_code": "livepatch-invalidates-fips"}, {"name": "fips-updates", "reason": "FIPS cannot be enabled if FIPS Updates has ever been enabled because FIPS Updates installs security patches that aren't officially certified.", "reason_code": "fips-updates-invalidates-fips"}], "description": "NIST-certified core packages", "description_override": null, "entitled": "yes", "name": "fips", "status": "n/a", "status_details": "Cannot enable FIPS when FIPS Updates is enabled.", "warning": null}
        """
        When I run `pro disable <fips-service> --assume-yes` with sudo
        And I run `pro enable <fips-service> --assume-yes --format json --assume-yes` with sudo
        Then stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
        """
        {"_schema_version": "0.1", "errors": [], "failed_services": [], "needs_reboot": true, "processed_services": ["<fips-service>"], "result": "success", "warnings": []}
        """
        When I reboot the machine
        And I run `pro disable <fips-service> --assume-yes --format json` with sudo
        Then stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
        """
        {"_schema_version": "0.1", "errors": [], "failed_services": [], "needs_reboot": true, "processed_services": ["<fips-service>"], "result": "success", "warnings": []}
        """
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
            """
            <fips-service> +yes                disabled
            """

        Examples: ubuntu release
           | release | fips-name    | fips-service |fips-apt-source                                                |
           | xenial  | FIPS Updates | fips-updates |https://esm.ubuntu.com/fips-updates/ubuntu xenial-updates/main |
           | bionic  | FIPS Updates | fips-updates |https://esm.ubuntu.com/fips-updates/ubuntu bionic-updates/main |

    @slow
    @series.xenial
    @series.bionic
    @uses.config.machine_type.lxd-vm
    Scenario Outline: Attached enable FIPS-updates while livepatch is enabled
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
            """
            fips-updates +yes                disabled
            """
        Then stdout matches regexp:
            """
            livepatch +yes +<livepatch_status>
            """
        When I run `pro enable fips-updates --assume-yes` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            Installing FIPS Updates packages
            FIPS Updates enabled
            A reboot is required to complete install
            """
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
            """
            fips-updates +yes                enabled
            """
        Then stdout matches regexp:
            """
            livepatch +yes +<livepatch_status>
            """
        When I reboot the machine
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
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
            """
            fips-updates +yes                enabled
            """
        Then stdout matches regexp:
            """
            livepatch +yes +enabled
            """
        Examples: ubuntu release
           | release | livepatch_status |
           | xenial  | warning          |
           | bionic  | enabled          |

    @slow
    @series.focal
    @uses.config.machine_type.lxd-vm
    Scenario Outline: Attached enable of FIPS in an ubuntu lxd vm
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `DEBIAN_FRONTEND=noninteractive apt-get install -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -y openssh-client openssh-server strongswan` with sudo, retrying exit [100]
        When I run `pro enable <fips-service> --assume-yes` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            Installing <fips-name> packages
            <fips-name> enabled
            A reboot is required to complete install
            """
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
            """
            <fips-service> +yes                enabled
            """
        And I verify that running `apt update` `with sudo` exits `0`
        And I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`
        When I reboot the machine
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
        When I run `pro disable <fips-service> --assume-yes` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            A reboot is required to complete disable operation
            """
        When I reboot the machine
        Then I verify that `openssh-server` installed version matches regexp `fips`
        And I verify that `openssh-client` installed version matches regexp `fips`
        And I verify that `strongswan` installed version matches regexp `fips`
        And I verify that `strongswan-hmac` installed version matches regexp `fips`
        When I run `apt-mark unhold openssh-client openssh-server strongswan` with sudo
        Then I will see the following on stdout:
        """
        openssh-client was already not hold.
        openssh-server was already not hold.
        strongswan was already not hold.
        """
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
            """
            <fips-service> +yes                disabled
            """

        Examples: ubuntu release
           | release | fips-name    | fips-service |fips-apt-source                               |
           | focal   | FIPS         | fips         |https://esm.ubuntu.com/fips/ubuntu focal/main |

    @slow
    @series.focal
    @uses.config.machine_type.lxd-vm
    Scenario Outline: Attached enable of FIPS-updates in an ubuntu lxd vm
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `DEBIAN_FRONTEND=noninteractive apt-get install -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -y openssh-client openssh-server strongswan` with sudo, retrying exit [100]
        When I run `pro enable <fips-service> --assume-yes` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            Installing <fips-name> packages
            <fips-name> enabled
            A reboot is required to complete install
            """
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
            """
            <fips-service> +yes                enabled
            """
        And I verify that running `apt update` `with sudo` exits `0`
        And I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`
        When I reboot the machine
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
        When I run `pro disable <fips-service> --assume-yes` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            A reboot is required to complete disable operation
            """
        When I reboot the machine
        Then I verify that `openssh-server` installed version matches regexp `fips`
        And I verify that `openssh-client` installed version matches regexp `fips`
        And I verify that `strongswan` installed version matches regexp `fips`
        And I verify that `strongswan-hmac` installed version matches regexp `fips`
        When I run `apt-mark unhold openssh-client openssh-server strongswan` with sudo
        Then I will see the following on stdout:
        """
        openssh-client was already not hold.
        openssh-server was already not hold.
        strongswan was already not hold.
        """
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
            """
            <fips-service> +yes                disabled
            """
        When I verify that running `pro enable fips --assume-yes` `with sudo` exits `1`
        Then stdout matches regexp:
            """
            Cannot enable FIPS because FIPS Updates was once enabled.
            """
        And I verify that files exist matching `/var/lib/ubuntu-advantage/services-once-enabled`

        Examples: ubuntu release
           | release | fips-name    | fips-service |fips-apt-source                                               |
           | focal   | FIPS Updates | fips-updates |https://esm.ubuntu.com/fips-updates/ubuntu focal-updates/main |

    @slow
    @series.lts
    @uses.config.machine_type.lxd-vm
    Scenario Outline: Attached enable fips-updates on fips enabled vm
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `pro enable fips --assume-yes` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            Installing FIPS packages
            FIPS enabled
            A reboot is required to complete install
            """
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
            """
            fips +yes                enabled
            """
        When I reboot the machine
        And  I run `uname -r` as non-root
        Then stdout matches regexp:
            """
            fips
            """
        When I verify that running `pro enable fips-updates --assume-yes` `with sudo` exits `0`
        Then stdout matches regexp:
            """
            One moment, checking your subscription first
            Disabling incompatible service: FIPS
            Updating package lists
            Installing FIPS Updates packages
            FIPS Updates enabled
            A reboot is required to complete install.
            """
            When I run `pro status --all` with sudo
            Then stdout matches regexp:
                """
                fips-updates +yes                enabled
                """
            And stdout matches regexp:
                """
                fips +yes                n/a
                """
            When I reboot the machine
            And  I run `pro enable livepatch` with sudo
            And I run `pro status --all` with sudo
            Then stdout matches regexp:
                """
                fips-updates +yes                enabled
                """
            And stdout matches regexp:
                """
                fips +yes                n/a
                """
            And stdout matches regexp:
                """
                livepatch +yes                (enabled|warning)
                """
            When  I run `uname -r` as non-root
            Then stdout matches regexp:
                """
                fips
                """
            When I run `cat /proc/sys/crypto/fips_enabled` with sudo
            Then I will see the following on stdout:
            """
            1
            """

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |

    @slow
    @series.xenial
    @series.bionic
    @uses.config.machine_type.lxd-vm
    Scenario Outline: FIPS enablement message when cloud init didn't run properly
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I delete the file `/run/cloud-init/instance-data.json`
        And I attach `contract_token` with sudo
        And I run `pro disable livepatch` with sudo
        And I run `pro enable fips --assume-yes` with sudo
        Then stderr matches regexp:
        """
        Could not determine cloud, defaulting to generic FIPS package.
        """
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
        """
        fips +yes                enabled
        """

        Examples: ubuntu release
        | release |
        | xenial  |
        | bionic  |

    @slow
    @series.focal
    @uses.config.machine_type.lxd-vm
    Scenario Outline: FIPS enablement message when cloud init didn't run properly
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I delete the file `/run/cloud-init/instance-data.json`
        And I attach `contract_token` with sudo
        And I run `pro enable fips --assume-yes` with sudo
        Then stderr matches regexp:
        """
        Could not determine cloud, defaulting to generic FIPS package.
        """
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
        """
        fips +yes                enabled
        """

        Examples: ubuntu release
        | release |
        | focal   |
