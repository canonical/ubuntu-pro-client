Feature: Command behaviour when unattached

    @series.all
    @uses.config.machine_type.lxd.container
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
            Auto-attach image support is not available on lxd
            See: https://ubuntu.com/advantage
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | xenial  |
           | hirsute |

    @series.xenial
    @uses.config.machine_type.lxd.container
    Scenario Outline: Disabled unattached APT policy apt-hook for infra and apps
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt update` with sudo
        When I run `apt-cache policy` with sudo
        Then stdout matches regexp:
        """
        -32768 <esm-infra-url> <release>-infra-updates/main amd64 Packages
        """
        And stdout does not match regexp:
        """
        -32768 <esm-apps-url> <release>-apps-updates/main amd64 Packages
        """
        And stdout does not match regexp:
        """
        -32768 <esm-apps-url> <release>-apps-security/main amd64 Packages
        """
        When I append the following on uaclient config:
            """
            features:
              allow_beta: true
            """
        And I run `dpkg-reconfigure ubuntu-advantage-tools` with sudo
        And I run `apt-get update` with sudo
        When I run `apt-cache policy` with sudo
        Then stdout matches regexp:
        """
        -32768 <esm-apps-url> <release>-apps-updates/main amd64 Packages
        """
        And stdout matches regexp:
        """
        -32768 <esm-apps-url> <release>-apps-security/main amd64 Packages
        """
        When I append the following on uaclient config:
            """
            features:
              allow_beta: true
            """
        And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout matches regexp:
        """
        \* Introducing Extended Security Maintenance for Applications.
          +Receive updates to over 30,000 software packages with your
          +Ubuntu Advantage subscription. Free for personal use.

            +https:\/\/ubuntu.com\/16-04

        UA Infra: Extended Security Maintenance \(ESM\) is not enabled.
        """
        # Check that json hook is installed properly
        When I run `ls /usr/lib/ubuntu-advantage` with sudo
        Then stdout matches regexp:
        """
        apt-esm-json-hook
        """
        When I run `cat /etc/apt/apt.conf.d/20apt-esm-hook.conf` with sudo
        Then stdout matches regexp:
        """
        apt-esm-json-hook
        """
        When I create the file `/etc/apt/sources.list.d/empty-release-origin.list` with the following
        """
        deb [ allow-insecure=yes ] https://packages.irods.org/apt xenial main
        """
        Then I verify that running `apt-get update` `with sudo` exits `0`
        When I delete the file `/var/lib/ubuntu-advantage/jobs-status.json`
        And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        Then I verify that running `/usr/lib/ubuntu-advantage/apt-esm-hook process-templates` `with sudo` exits `0`

        Examples: ubuntu release
           | release | esm-infra-url                       | esm-apps-url |
           | xenial  | https://esm.ubuntu.com/infra/ubuntu | https://esm.ubuntu.com/apps/ubuntu |

    @series.all
    @uses.config.machine_type.lxd.container
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
            See https://ubuntu.com/advantage
            """

        Examples: ua commands
           | release | command |
           | bionic  | detach  |
           | bionic  | refresh |
           | focal   | detach  |
           | focal   | refresh |
           | xenial  | detach  |
           | xenial  | refresh |
           | hirsute | detach  |
           | hirsute | refresh |

    @series.all
    @uses.config.machine_type.lxd.container
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
            See https://ubuntu.com/advantage
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
           | xenial  | enable   | livepatch |
           | xenial  | disable  | livepatch |
           | xenial  | enable   | unknown   |
           | xenial  | disable  | unknown   |
           | hirsute | enable   | livepatch |
           | hirsute | disable  | livepatch |
           | hirsute | enable   | unknown   |
           | hirsute | disable  | unknown   |

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Help command on an unattached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `ua help esm-infra` as non-root
        Then I will see the following on stdout:
            """
            Name:
            esm-infra

            Available:
            <infra-status>

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
            {"name": "esm-infra", "available": "<infra-status>", "help": "esm-infra provides access to a private ppa which includes available high\nand critical CVE fixes for Ubuntu LTS packages in the Ubuntu Main\nrepository between the end of the standard Ubuntu LTS security\nmaintenance and its end of life. It is enabled by default with\nExtended Security Maintenance (ESM) for UA Apps and UA Infra.\nYou can find our more about the esm service at\nhttps://ubuntu.com/security/esm\n"}
            """
        When I verify that running `ua help invalid-service` `with sudo` exits `1`
        Then I will see the following on stderr:
            """
            No help available for 'invalid-service'
            """

        Examples: ubuntu release
           | release  | infra-status |
           | bionic   | yes          |
           | focal    | yes          |
           | xenial   | yes          |
           | hirsute  | no           |


    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Useful SSL failure message when there aren't any ca-certs
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt remove ca-certificates -y` with sudo
        When I verify that running `ua fix CVE-1800-123456` `as non-root` exits `1`
        Then I will see the following on stderr:
            """
            Failed to access URL: https://ubuntu.com/security/cves/CVE-1800-123456.json
            Cannot verify certificate of server
            Please install "ca-certificates" and try again.
            """
        When I run `apt install ca-certificates -y` with sudo
        When I run `mv /etc/ssl/certs /etc/ssl/wronglocation` with sudo
        When I verify that running `ua fix CVE-1800-123456` `as non-root` exits `1`
        Then I will see the following on stderr:
            """
            Failed to access URL: https://ubuntu.com/security/cves/CVE-1800-123456.json
            Cannot verify certificate of server
            Please check your openssl configuration.
            """
        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | hirsute |


    @series.focal
    @uses.config.machine_type.lxd.container
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
            Found CVEs:
            https://ubuntu.com/security/CVE-2020-11728
            1 affected package is installed: awl
            \(1/1\) awl:
            A fix is available in Ubuntu standard updates.
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
    @uses.config.machine_type.lxd.container
    Scenario Outline: Fix command on an unattached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt install -y libawl-php` with sudo
        And I run `ua fix USN-4539-1` as non-root
        Then stdout matches regexp:
            """
            USN-4539-1: AWL vulnerability
            Found CVEs:
            https://ubuntu.com/security/CVE-2020-11728
            1 affected package is installed: awl
            \(1/1\) awl:
            Sorry, no fix is available.
            1 package is still affected: awl
            .*✘.* USN-4539-1 is not resolved.
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
            A fix is available in Ubuntu standard updates.
            The update is already installed.
            .*✔.* CVE-2020-28196 is resolved.
            """
        When I run `DEBIAN_FRONTEND=noninteractive apt-get install -y expat=2.1.0-7 swish-e matanza ghostscript` with sudo
        And I verify that running `ua fix CVE-2017-9233` `with sudo` exits `1`
        Then stdout matches regexp:
            """
            CVE-2017-9233: Expat vulnerability
            https://ubuntu.com/security/CVE-2017-9233
            3 affected packages are installed: expat, matanza, swish-e
            \(1/3, 2/3\) matanza, swish-e:
            Sorry, no fix is available.
            """
        And stderr matches regexp:
            """
            Error: CVE-2017-9233 metadata defines no fixed version for expat.
            3 packages are still affected: expat, matanza, swish-e
            .*✘.* CVE-2017-9233 is not resolved.
            """

        Examples: ubuntu release details
           | release |
           | xenial  |

    @series.bionic
    @uses.config.machine_type.lxd.container
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
            Found CVEs:
            https://ubuntu.com/security/CVE-2020-11728
            1 affected package is installed: awl
            \(1/1\) awl:
            Ubuntu security engineers are investigating this issue.
            1 package is still affected: awl
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
        Package fixes cannot be installed.
        To install them, run this command as root \(try using sudo\)
        1 package is still affected: xterm
        .*✘.* CVE-2021-27135 is not resolved.
        """
        When I run `ua fix CVE-2021-27135` with sudo
        Then stdout matches regexp:
        """
        CVE-2021-27135: xterm vulnerability
        https://ubuntu.com/security/CVE-2021-27135
        1 affected package is installed: xterm
        \(1/1\) xterm:
        A fix is available in Ubuntu standard updates.
        .*\{ apt update && apt install --only-upgrade -y xterm \}.*
        .*✔.* CVE-2021-27135 is resolved.
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
