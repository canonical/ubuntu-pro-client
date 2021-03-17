Feature: Command behaviour when unattached

    @series.all
    Scenario Outline: Unattached auto-attach does nothing in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I verify that running `ua auto-attach` `as non-root` exits `1`
        Then stderr matches regexp:
            """
            This command must be run as root \(try using sudo\).
            """
        When I run `ua auto-attach` with sudo
        Then stderr matches regexp:
            """
            Auto-attach image support is not available on <data>
            See: https://ubuntu.com/advantage.
            """

        Examples: ubuntu release
           | release | data       |
           | bionic  | lxd        |
           | focal   | lxd        |
           | trusty  | nocloudnet |
           | xenial  | lxd        |

    @series.all
    Scenario Outline: Unattached commands that requires enabled user in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I verify that running `ua <command>` `as non-root` exits `1`
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo).
            """
        When I verify that running `ua <command>` `with sudo` exits `1`
        Then stderr matches regexp:
            """
            This machine is not attached to a UA subscription.
            See https://ubuntu.com/advantage.
            """

        Examples: ua commands
           | release | command |
           | bionic  | detach  |
           | bionic  | refresh |
           | focal   | detach  |
           | focal   | refresh |
           | trusty  | detach  |
           | trusty  | refresh |
           | xenial  | detach  |
           | xenial  | refresh |

    @series.all
    Scenario Outline: Unattached command known and unknown services in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I verify that running `ua <command> <service>` `as non-root` exits `1`
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo).
            """
        When I verify that running `ua <command> <service>` `with sudo` exits `1`
        Then stderr matches regexp:
            """
            To use '<service>' you need an Ubuntu Advantage subscription
            Personal and community subscriptions are available at no charge
            See https://ubuntu.com/advantage.
            """

        Examples: ua commands
           | release | command  | service   |
           | bionic  | enable   | livepatch |
           | bionic  | disable  | livepatch |
           | bionic  | enable   | unknown   |
           | bionic  | disable  | unknown   |
           | focal   | enable   | livepatch |
           | focal   | disable  | livepatch |
           | focal   | enable   | unknown   |
           | focal   | disable  | unknown   |
           | trusty  | enable   | livepatch |
           | trusty  | disable  | livepatch |
           | trusty  | enable   | unknown   |
           | trusty  | disable  | unknown   |
           | xenial  | enable   | livepatch |
           | xenial  | disable  | livepatch |
           | xenial  | enable   | unknown   |
           | xenial  | disable  | unknown   |

    @series.all
    Scenario Outline: Help command on an unattached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `ua help esm-infra` as non-root
        Then I will see the following on stdout:
            """
            Name:
            esm-infra

            Available:
            yes

            Help:
            esm-infra provides access to a private ppa which includes available high
            and critical CVE fixes for Ubuntu LTS packages in the Ubuntu Main
            repository between the end of the standard Ubuntu LTS security
            maintenance and its end of life. It is enabled by default with
            Extended Security Maintenance (ESM) for UA Apps and UA Infra.
            You can find our more about the esm service at
            https://ubuntu.com/security/esm
            """
        When I run `ua help esm-infra --format json` with sudo
        Then I will see the following on stdout:
            """
            {"name": "esm-infra", "available": "yes", "help": "esm-infra provides access to a private ppa which includes available high\nand critical CVE fixes for Ubuntu LTS packages in the Ubuntu Main\nrepository between the end of the standard Ubuntu LTS security\nmaintenance and its end of life. It is enabled by default with\nExtended Security Maintenance (ESM) for UA Apps and UA Infra.\nYou can find our more about the esm service at\nhttps://ubuntu.com/security/esm\n"}
            """
        When I verify that running `ua help invalid-service` `with sudo` exits `1`
        Then I will see the following on stderr:
            """
            No help available for 'invalid-service'
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | trusty  |
           | xenial  |

    @series.focal
    Scenario Outline: Fix command on an unattached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I verify that running `ua fix CVE-1800-123456` `as non-root` exits `1`
        Then I will see the following on stderr:
            """
            Error: CVE-1800-123456 not found.
            """
        When I verify that running `ua fix USN-12345-12` `as non-root` exits `1`
        Then I will see the following on stderr:
            """
            Error: USN-12345-12 not found.
            """
        When I verify that running `ua fix CVE-12345678-12` `as non-root` exits `1`
        Then I will see the following on stderr:
            """
            Error: issue "CVE-12345678-12" is not recognized.
            Usage: "ua fix CVE-yyyy-nnnn" or "ua fix USN-nnnn"
            """
        When I verify that running `ua fix USN-12345678-12` `as non-root` exits `1`
        Then I will see the following on stderr:
            """
            Error: issue "USN-12345678-12" is not recognized.
            Usage: "ua fix CVE-yyyy-nnnn" or "ua fix USN-nnnn"
            """
        When I run `apt install -y libawl-php=0.60-1 --allow-downgrades` with sudo
        And I run `ua fix USN-4539-1` with sudo
        Then stdout matches regexp:
            """
            USN-4539-1: AWL vulnerability
            https://ubuntu.com/security/notices/USN-4539-1
            Related CVEs: CVE-2020-11728.
            1 affected package is installed: awl
            \(1/1\) awl:
            A fix is available in Ubuntu standard updates.
            The update is not yet installed.
            .*\{ apt update && apt install --only-upgrade -y libawl-php \}.*
            .*✔.* USN-4539-1 is resolved.
            """
        When I run `ua fix CVE-2020-28196` as non-root
        Then stdout matches regexp:
            """
            CVE-2020-28196: Kerberos vulnerability
            https://ubuntu.com/security/CVE-2020-28196
            1 affected package is installed: krb5
            \(1/1\) krb5:
            A fix is available in Ubuntu standard updates.
            The update is already installed.
            .*✔.* CVE-2020-28196 is resolved.
            """

        Examples: ubuntu release details
           | release |
           | focal   |

    @series.xenial
    Scenario Outline: Fix command on an unattached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt install -y libawl-php` with sudo
        And I run `ua fix USN-4539-1` as non-root
        Then stdout matches regexp:
            """
            USN-4539-1: AWL vulnerability
            https://ubuntu.com/security/notices/USN-4539-1
            Related CVEs: CVE-2020-11728.
            1 affected package is installed: awl
            \(1/1\) awl:
            Ubuntu security engineers are investigating this issue.
            .*✘.* USN-4539-1 is not resolved.
            """
        When I run `ua fix CVE-2020-28196` as non-root
        Then stdout matches regexp:
            """
            CVE-2020-28196: Kerberos vulnerability
            https://ubuntu.com/security/CVE-2020-28196
            1 affected package is installed: krb5
            \(1/1\) krb5:
            A fix is available in Ubuntu standard updates.
            The update is already installed.
            .*✔.* CVE-2020-28196 is resolved.
            """
        When I run `DEBIAN_FRONTEND=noninteractive apt-get install -y expat=2.1.0-7 swish-e matanza` with sudo
        And I run `ua fix CVE-2017-9233` with sudo
        Then stdout matches regexp:
            """
            CVE-2017-9233: Expat vulnerability
            https://ubuntu.com/security/CVE-2017-9233
            3 affected packages are installed: expat, matanza, swish-e
            \(1/3, 2/3\) matanza, swish-e:
            Ubuntu security engineers are investigating this issue.
            \(3/3\) expat:
            A fix is available in Ubuntu standard updates.
            The update is not yet installed.
            .*\{ apt update && apt install --only-upgrade -y expat \}.*
            .*✘.* CVE-2017-9233 is not resolved.
            """
        When I run `ua fix CVE-2017-9233` with sudo
        Then stdout matches regexp:
            """
            CVE-2017-9233: Expat vulnerability
            https://ubuntu.com/security/CVE-2017-9233
            3 affected packages are installed: expat, matanza, swish-e
            \(1/3, 2/3\) matanza, swish-e:
            Ubuntu security engineers are investigating this issue.
            \(3/3\) expat:
            A fix is available in Ubuntu standard updates.
            """
        Then stderr matches regexp:
            """
            Error: CVE-2017-9233 metadata defines no fixed version for expat.
            .*✘.* CVE-2017-9233 is not resolved.
            """

        Examples: ubuntu release details
           | release |
           | xenial  |


    @series.trusty
    Scenario Outline: Fix command on an unattached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `ua fix USN-4539-1` as non-root
        Then stdout matches regexp:
            """
            USN-4539-1: AWL vulnerability
            https://ubuntu.com/security/notices/USN-4539-1
            Related CVEs: CVE-2020-11728.
            No affected packages are installed.
            .*✔.* USN-4539-1 does not affect your system.
            """
        When I run `ua fix CVE-2020-15180` as non-root
        Then stdout matches regexp:
            """
            CVE-2020-15180: MariaDB vulnerabilities
            https://ubuntu.com/security/CVE-2020-15180
            No affected packages are installed.
            .*✔.* CVE-2020-15180 does not affect your system.
            """
        When I run `ua fix CVE-2020-28196` as non-root
        Then stdout matches regexp:
            """
            CVE-2020-28196: Kerberos vulnerability
            https://ubuntu.com/security/CVE-2020-28196
            1 affected package is installed: krb5
            \(1/1\) krb5:
            A fix is available in UA Infra.
            The update is not yet installed.
            Package fixes cannot be installed.
            To install them, run this command as root \(try using sudo\)
            """

        Examples: ubuntu release
           | release |
           | trusty  |

    @series.bionic
    Scenario: Fix command on an unattached machine
        Given a `bionic` machine with ubuntu-advantage-tools installed
        When I verify that running `ua fix CVE-1800-123456` `as non-root` exits `1`
        Then I will see the following on stderr:
            """
            Error: CVE-1800-123456 not found.
            """
        When I verify that running `ua fix USN-12345-12` `as non-root` exits `1`
        Then I will see the following on stderr:
            """
            Error: USN-12345-12 not found.
            """
        When I verify that running `ua fix CVE-12345678-12` `as non-root` exits `1`
        Then I will see the following on stderr:
            """
            Error: issue "CVE-12345678-12" is not recognized.
            Usage: "ua fix CVE-yyyy-nnnn" or "ua fix USN-nnnn"
            """
        When I verify that running `ua fix USN-12345678-12` `as non-root` exits `1`
        Then I will see the following on stderr:
            """
            Error: issue "USN-12345678-12" is not recognized.
            Usage: "ua fix CVE-yyyy-nnnn" or "ua fix USN-nnnn"
            """
        When I run `apt install -y libawl-php` with sudo
        And I run `ua fix USN-4539-1` as non-root
        Then stdout matches regexp:
            """
            USN-4539-1: AWL vulnerability
            https://ubuntu.com/security/notices/USN-4539-1
            Related CVEs: CVE-2020-11728.
            1 affected package is installed: awl
            \(1/1\) awl:
            Ubuntu security engineers are investigating this issue.
            .*✘.* USN-4539-1 is not resolved.
            """
        When I run `ua fix CVE-2020-28196` as non-root
        Then stdout matches regexp:
            """
            CVE-2020-28196: Kerberos vulnerability
            https://ubuntu.com/security/CVE-2020-28196
            1 affected package is installed: krb5
            \(1/1\) krb5:
            A fix is available in Ubuntu standard updates.
            The update is already installed.
            .*✔.* CVE-2020-28196 is resolved.
            """
        When I run `apt-get install xterm=330-1ubuntu2 -y` with sudo
        And I run `ua fix CVE-2021-27135` as non-root
        Then stdout matches regexp:
        """
        CVE-2021-27135: xterm vulnerability
        https://ubuntu.com/security/CVE-2021-27135
        1 affected package is installed: xterm
        \(1/1\) xterm:
        A fix is available in Ubuntu standard updates.
        The update is not yet installed.
        Package fixes cannot be installed.
        To install them, run this command as root \(try using sudo\)
        """
        When I run `ua fix CVE-2021-27135` with sudo
        Then stdout matches regexp:
        """
        CVE-2021-27135: xterm vulnerability
        https://ubuntu.com/security/CVE-2021-27135
        1 affected package is installed: xterm
        \(1/1\) xterm:
        A fix is available in Ubuntu standard updates.
        The update is not yet installed.
        .*\{ apt update && apt install --only-upgrade -y xterm \}.*
        """
        When I run `ua fix CVE-2021-27135` with sudo
        Then stdout matches regexp:
        """
        CVE-2021-27135: xterm vulnerability
        https://ubuntu.com/security/CVE-2021-27135
        1 affected package is installed: xterm
        \(1/1\) xterm:
        A fix is available in Ubuntu standard updates.
        The update is already installed.
        .*✔.* CVE-2021-27135 is resolved.
        """
