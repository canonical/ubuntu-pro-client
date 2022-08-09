Feature: FIPS enablement in PRO cloud based machines

    @slow
    @series.bionic
    @series.focal
    @uses.config.machine_type.aws.pro
    Scenario Outline: Attached enable of FIPS in an ubuntu Azure PRO vm
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        And I run `pro auto-attach` with sudo
        And I run `pro status --wait` with sudo
        Then stdout matches regexp:
            """
            fips          +yes +disabled +NIST-certified core packages
            fips-updates  +yes +disabled +NIST-certified core packages with priority security updates
            """
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
            And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
            When I run `apt-cache policy ubuntu-aws-fips` as non-root
            Then stdout does not match regexp:
            """
            .*Installed: \(none\)
            """
            When I reboot the machine
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

        Examples: ubuntu release
           | release | fips-name    | fips-service |fips-apt-source                                |
           | bionic  | FIPS         | fips         |https://esm.ubuntu.com/fips/ubuntu bionic/main |
           | bionic  | FIPS Updates | fips-updates |https://esm.ubuntu.com/fips/ubuntu bionic/main |
           | focal   | FIPS         | fips         |https://esm.ubuntu.com/fips/ubuntu focal/main  |
           | focal   | FIPS Updates | fips-updates |https://esm.ubuntu.com/fips/ubuntu focal/main  |

    @slow
    @series.bionic
    @series.focal
    @uses.config.machine_type.azure.pro
    Scenario Outline: Attached enable of FIPS in an ubuntu Azure PRO vm
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        And I run `pro auto-attach` with sudo
        And I run `pro status --wait` with sudo
        Then stdout matches regexp:
            """
            fips          +yes +disabled +NIST-certified core packages
            fips-updates  +yes +disabled +NIST-certified core packages with priority security updates
            """
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
            And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
            When I run `apt-cache policy ubuntu-azure-fips` as non-root
            Then stdout does not match regexp:
            """
            .*Installed: \(none\)
            """
            When I reboot the machine
            And  I run `uname -r` as non-root
            Then stdout matches regexp:
                """
                azure-fips
                """
            When I run `cat /proc/sys/crypto/fips_enabled` with sudo
            Then I will see the following on stdout:
            """
            1
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
    @uses.config.machine_type.gcp.pro
    Scenario Outline: Attached enable of FIPS in an ubuntu GCP PRO vm
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        And I run `pro auto-attach` with sudo
        And I run `pro status --wait` with sudo
        Then stdout matches regexp:
            """
            fips          +yes +disabled +NIST-certified core packages
            fips-updates  +yes +disabled +NIST-certified core packages with priority security updates
            """
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
        And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
        When I run `apt-cache policy ubuntu-gcp-fips` as non-root
        Then stdout does not match regexp:
            """
            .*Installed: \(none\)
            """
        When I reboot the machine
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

        Examples: ubuntu release
           | release | fips-name    | fips-service |fips-apt-source                                |
           | bionic  | FIPS         | fips         |https://esm.ubuntu.com/fips/ubuntu bionic/main |
           | bionic  | FIPS Updates | fips-updates |https://esm.ubuntu.com/fips/ubuntu bionic/main |
           | focal   | FIPS         | fips         |https://esm.ubuntu.com/fips/ubuntu focal/main  |
           | focal   | FIPS Updates | fips-updates |https://esm.ubuntu.com/fips/ubuntu focal/main  |
