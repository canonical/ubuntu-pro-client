Feature: Ua fix command behaviour

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Useful SSL failure message when there aren't any ca-certs
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `mv /etc/ssl/certs /etc/ssl/wronglocation` with sudo
        When I verify that running `ua fix CVE-1800-123456` `as non-root` exits `1`
        Then stderr matches regexp:
            """
            Failed to access URL: https://.*
            Cannot verify certificate of server
            Please check your openssl configuration.
            """
        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | impish  |
           | jammy   |

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
            1 affected source package is installed: awl
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
            1 affected source package is installed: krb5
            \(1/1\) krb5:
            A fix is available in Ubuntu standard updates.
            The update is already installed.
            .*✔.* CVE-2020-28196 is resolved.
            """
        When I run `ua fix CVE-2022-24959` as non-root
        Then stdout matches regexp:
            """
            CVE-2022-24959: Linux kernel vulnerabilities
            https://ubuntu.com/security/CVE-2022-24959
            No affected source packages are installed.
            .*✔.* CVE-2022-24959 does not affect your system.
            """

        Examples: ubuntu release details
           | release |
           | focal   |

    @series.xenial
    @uses.config.contract_token
    @uses.config.machine_type.lxd.container
    Scenario Outline: Fix command on an unattached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt install -y libawl-php` with sudo
        And I reboot the `<release>` machine
        And I verify that running `ua fix USN-4539-1` `as non-root` exits `1`
        Then stdout matches regexp:
        """
        USN-4539-1: AWL vulnerability
        Found CVEs:
        https://ubuntu.com/security/CVE-2020-11728
        1 affected source package is installed: awl
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
        No affected source packages are installed.
        .*✔.* CVE-2020-15180 does not affect your system.
        """
        When I run `ua fix CVE-2020-28196` as non-root
        Then stdout matches regexp:
        """
        CVE-2020-28196: Kerberos vulnerability
        https://ubuntu.com/security/CVE-2020-28196
        1 affected source package is installed: krb5
        \(1/1\) krb5:
        A fix is available in Ubuntu standard updates.
        The update is already installed.
        .*✔.* CVE-2020-28196 is resolved.
        """
        When I run `DEBIAN_FRONTEND=noninteractive apt-get install -y expat=2.1.0-7 swish-e matanza ghostscript` with sudo
        And I verify that running `ua fix CVE-2017-9233 --dry-run` `as non-root` exits `1`
        Then stdout matches regexp:
        """
        .*WARNING: The option --dry-run is being used.
        No packages will be installed when running this command..*
        CVE-2017-9233: Expat vulnerability
        https://ubuntu.com/security/CVE-2017-9233
        3 affected source packages are installed: expat, matanza, swish-e
        \(1/3, 2/3\) matanza, swish-e:
        Sorry, no fix is available.
        \(3/3\) expat:
        A fix is available in Ubuntu standard updates.
        .*\{ apt update && apt install --only-upgrade -y expat \}.*
        2 packages are still affected: matanza, swish-e
        .*✘.* CVE-2017-9233 is not resolved.
        """
        When I verify that running `ua fix CVE-2017-9233` `with sudo` exits `1`
        Then stdout matches regexp:
        """
        CVE-2017-9233: Expat vulnerability
        https://ubuntu.com/security/CVE-2017-9233
        3 affected source packages are installed: expat, matanza, swish-e
        \(1/3, 2/3\) matanza, swish-e:
        Sorry, no fix is available.
        \(3/3\) expat:
        A fix is available in Ubuntu standard updates.
        .*\{ apt update && apt install --only-upgrade -y expat \}.*
        2 packages are still affected: matanza, swish-e
        .*✘.* CVE-2017-9233 is not resolved.
        """
        When I run `ua fix USN-5079-2 --dry-run` as non-root
        Then stdout matches regexp:
        """
        .*WARNING: The option --dry-run is being used.
        No packages will be installed when running this command..*
        USN-5079-2: curl vulnerabilities
        Found CVEs:
        https://ubuntu.com/security/CVE-2021-22946
        https://ubuntu.com/security/CVE-2021-22947
        1 affected source package is installed: curl
        \(1/1\) curl:
        A fix is available in UA Infra.
        .*The machine is not attached to an Ubuntu Advantage \(UA\) subscription.
        To proceed with the fix, a prompt would ask for a valid UA token.
        \{ ua attach TOKEN \}.*
        .*UA service: esm-infra is not enabled.
        To proceed with the fix, a prompt would ask permission to automatically enable
        this service.
        \{ ua enable esm-infra \}.*
        .*\{ apt update && apt install --only-upgrade -y curl libcurl3-gnutls \}.*
        .*✔.* USN-5079-2 is resolved.
        """
        When I fix `USN-5079-2` by attaching to a subscription with `contract_token_staging_expired`
        Then stdout matches regexp
        """
        USN-5079-2: curl vulnerabilities
        Found CVEs:
        https://ubuntu.com/security/CVE-2021-22946
        https://ubuntu.com/security/CVE-2021-22947
        1 affected source package is installed: curl
        \(1/1\) curl:
        A fix is available in UA Infra.
        The update is not installed because this system is not attached to a
        subscription.

        Choose: \[S\]ubscribe at ubuntu.com \[A\]ttach existing token \[C\]ancel
        > Enter your token \(from https://ubuntu.com/advantage\) to attach this system:
        > .*\{ ua attach .*\}.*
        Attach denied:
        Contract ".*" expired on .*
        Visit https://ubuntu.com/advantage to manage contract tokens.
        1 package is still affected: curl
        .*✘.* USN-5079-2 is not resolved.
        """
        When I fix `USN-5079-2` by attaching to a subscription with `contract_token`
        Then stdout matches regexp:
        """
        USN-5079-2: curl vulnerabilities
        Found CVEs:
        https://ubuntu.com/security/CVE-2021-22946
        https://ubuntu.com/security/CVE-2021-22947
        1 affected source package is installed: curl
        \(1/1\) curl:
        A fix is available in UA Infra.
        The update is not installed because this system is not attached to a
        subscription.

        Choose: \[S\]ubscribe at ubuntu.com \[A\]ttach existing token \[C\]ancel
        > Enter your token \(from https://ubuntu.com/advantage\) to attach this system:
        > .*\{ ua attach .*\}.*
        Updating package lists
        UA Apps: ESM enabled
        Updating package lists
        UA Infra: ESM enabled
        """
        And stdout matches regexp:
        """
        .*\{ apt update && apt install --only-upgrade -y curl libcurl3-gnutls \}.*
        .*✔.* USN-5079-2 is resolved.
        """
        When I verify that running `ua fix USN-5051-2` `with sudo` exits `2`
        Then stdout matches regexp:
        """
        USN-5051-2: OpenSSL vulnerability
        Found CVEs:
        https://ubuntu.com/security/CVE-2021-3712
        1 affected source package is installed: openssl
        \(1/1\) openssl:
        A fix is available in UA Infra.
        .*\{ apt update && apt install --only-upgrade -y libssl1.0.0 openssl \}.*
        A reboot is required to complete fix operation.
        .*✘.* USN-5051-2 is not resolved.
        """
        When I run `ua disable esm-infra` with sudo
        And I run `apt-get install gzip -y` with sudo
        And I run `ua fix USN-5378-4 --dry-run` as non-root
        Then stdout matches regexp:
        """
        .*WARNING: The option --dry-run is being used.
        No packages will be installed when running this command..*
        USN-5378-4: Gzip vulnerability
        Found CVEs:
        https://ubuntu.com/security/CVE-2022-1271
        2 affected source packages are installed: gzip, xz-utils
        \(1/2, 2/2\) gzip, xz-utils:
        A fix is available in UA Infra.
        .*UA service: esm-infra is not enabled.
        To proceed with the fix, a prompt would ask permission to automatically enable
        this service.
        \{ ua enable esm-infra \}.*
        .*\{ apt update && apt install --only-upgrade -y gzip liblzma5 xz-utils \}.*
        .*✔.* USN-5378-4 is resolved.
        """
        When I run `ua fix USN-5378-4` `with sudo` and stdin `E`
        Then stdout matches regexp:
        """
        USN-5378-4: Gzip vulnerability
        Found CVEs:
        https://ubuntu.com/security/CVE-2022-1271
        2 affected source packages are installed: gzip, xz-utils
        \(1/2, 2/2\) gzip, xz-utils:
        A fix is available in UA Infra.
        The update is not installed because this system does not have
        esm-infra enabled.

        Choose: \[E\]nable esm-infra \[C\]ancel
        > .*\{ ua enable esm-infra \}.*
        One moment, checking your subscription first
        Updating package lists
        UA Infra: ESM enabled
        .*\{ apt update && apt install --only-upgrade -y gzip liblzma5 xz-utils \}.*
        .*✔.* USN-5378-4 is resolved.
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
        And I verify that running `ua fix USN-4539-1 --dry-run` `as non-root` exits `1`
        Then stdout matches regexp:
        """
        .*WARNING: The option --dry-run is being used.
        No packages will be installed when running this command..*
        USN-4539-1: AWL vulnerability
        Found CVEs:
        https://ubuntu.com/security/CVE-2020-11728
        1 affected source package is installed: awl
        \(1/1\) awl:
        Ubuntu security engineers are investigating this issue.
        1 package is still affected: awl
        .*✘.* USN-4539-1 is not resolved.
        """
        When I verify that running `ua fix USN-4539-1` `as non-root` exits `1`
        Then stdout matches regexp:
        """
        USN-4539-1: AWL vulnerability
        Found CVEs:
        https://ubuntu.com/security/CVE-2020-11728
        1 affected source package is installed: awl
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
        1 affected source package is installed: krb5
        \(1/1\) krb5:
        A fix is available in Ubuntu standard updates.
        The update is already installed.
        .*✔.* CVE-2020-28196 is resolved.
        """
        When I run `apt-get install xterm=330-1ubuntu2 -y` with sudo
        And I verify that running `ua fix CVE-2021-27135` `as non-root` exits `1`
        Then stdout matches regexp:
        """
        CVE-2021-27135: xterm vulnerability
        https://ubuntu.com/security/CVE-2021-27135
        1 affected source package is installed: xterm
        \(1/1\) xterm:
        A fix is available in Ubuntu standard updates.
        Package fixes cannot be installed.
        To install them, run this command as root \(try using sudo\)
        1 package is still affected: xterm
        .*✘.* CVE-2021-27135 is not resolved.
        """
        When I run `ua fix CVE-2021-27135 --dry-run` with sudo
        Then stdout matches regexp:
        """
        .*WARNING: The option --dry-run is being used.
        No packages will be installed when running this command..*
        CVE-2021-27135: xterm vulnerability
        https://ubuntu.com/security/CVE-2021-27135
        1 affected source package is installed: xterm
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
        1 affected source package is installed: xterm
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
        1 affected source package is installed: xterm
        \(1/1\) xterm:
        A fix is available in Ubuntu standard updates.
        The update is already installed.
        .*✔.* CVE-2021-27135 is resolved.
        """
        When I run `apt-get install libbz2-1.0=1.0.6-8.1 -y --allow-downgrades` with sudo
        And I run `apt-get install bzip2=1.0.6-8.1 -y` with sudo
        And I run `ua fix USN-4038-3` with sudo
        Then stdout matches regexp:
        """
        USN-4038-3: bzip2 regression
        Found Launchpad bugs:
        https://launchpad.net/bugs/1834494
        1 affected source package is installed: bzip2
        \(1/1\) bzip2:
        A fix is available in Ubuntu standard updates.
        .*\{ apt update && apt install --only-upgrade -y bzip2 libbz2-1.0 \}.*
        .*✔.* USN-4038-3 is resolved.
        """


