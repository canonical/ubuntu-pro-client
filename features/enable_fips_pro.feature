Feature: FIPS enablement in PRO cloud based machines

    @slow
    Scenario Outline: Attached enable of FIPS in an ubuntu Aws PRO vm
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        log_level: debug
        """
        And I run `pro auto-attach` with sudo
        Then I verify that `fips` is disabled
        And I verify that `fips-updates` is disabled
        When I run `pro enable <fips-service> --assume-yes` with sudo
        Then stdout contains substring:
        """
        Updating <fips-name> package lists
        Installing <fips-name> packages
        Updating standard Ubuntu package lists
        <fips-name> enabled
        A reboot is required to complete install
        """
        And I verify that `<fips-service>` is enabled
        And I ensure apt update runs without errors
        And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
        When I run `apt-cache policy <package-name>` as non-root
        Then stdout does not match regexp:
        """
        .*Installed: \(none\)
        """
        When I reboot the machine
        And  I run `uname -r` as non-root
        Then stdout matches regexp:
        """
        <kernel-name>
        """
        When I run `cat /proc/sys/crypto/fips_enabled` with sudo
        Then I will see the following on stdout:
        """
        1
        """

        Examples: ubuntu release
           | release | machine_type | fips-name    | fips-service | package-name      | kernel-name | fips-apt-source                                |
           | bionic  | aws.pro      | FIPS         | fips         | ubuntu-aws-fips   | aws-fips    | https://esm.ubuntu.com/fips/ubuntu bionic/main |
           | bionic  | aws.pro      | FIPS Updates | fips-updates | ubuntu-aws-fips   | aws-fips    | https://esm.ubuntu.com/fips/ubuntu bionic/main |
           | bionic  | azure.pro    | FIPS         | fips         | ubuntu-azure-fips | azure-fips  | https://esm.ubuntu.com/fips/ubuntu bionic/main |
           | bionic  | azure.pro    | FIPS Updates | fips-updates | ubuntu-azure-fips | azure-fips  | https://esm.ubuntu.com/fips/ubuntu bionic/main |
           | bionic  | gcp.pro      | FIPS         | fips         | ubuntu-gcp-fips   | gcp-fips    | https://esm.ubuntu.com/fips/ubuntu bionic/main |
           | bionic  | gcp.pro      | FIPS Updates | fips-updates | ubuntu-gcp-fips   | gcp-fips    | https://esm.ubuntu.com/fips/ubuntu bionic/main |
           | focal   | aws.pro      | FIPS         | fips         | ubuntu-aws-fips   | aws-fips    | https://esm.ubuntu.com/fips/ubuntu focal/main  |
           | focal   | aws.pro      | FIPS Updates | fips-updates | ubuntu-aws-fips   | aws-fips    | https://esm.ubuntu.com/fips/ubuntu focal/main  |
           | focal   | azure.pro    | FIPS         | fips         | ubuntu-azure-fips | azure-fips  | https://esm.ubuntu.com/fips/ubuntu focal/main  |
           | focal   | azure.pro    | FIPS Updates | fips-updates | ubuntu-azure-fips | azure-fips  | https://esm.ubuntu.com/fips/ubuntu focal/main  |
           | focal   | gcp.pro      | FIPS         | fips         | ubuntu-gcp-fips   | gcp-fips    | https://esm.ubuntu.com/fips/ubuntu focal/main  |
           | focal   | gcp.pro      | FIPS Updates | fips-updates | ubuntu-gcp-fips   | gcp-fips    | https://esm.ubuntu.com/fips/ubuntu focal/main  |
