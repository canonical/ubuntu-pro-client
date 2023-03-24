Feature: Ua fix command behaviour

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Useful SSL failure message when there aren't any ca-certs
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get update` with sudo
        When I run `apt remove ca-certificates -y` with sudo
        When I verify that running `ua fix CVE-1800-123456` `as non-root` exits `1`
        Then stderr matches regexp:
            """
            Failed to access URL: https://.*
            Cannot verify certificate of server
            Please install "ca-certificates" and try again.
            """
        When I run `apt install ca-certificates -y` with sudo
        When I run `mv /etc/ssl/certs /etc/ssl/wronglocation` with sudo
        When I verify that running `pro fix CVE-1800-123456` `as non-root` exits `1`
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
           | jammy   |
           | kinetic |
           | lunar   |

    @series.focal
    @uses.config.machine_type.lxd.container
    Scenario Outline: Fix command on an unattached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get update` with sudo
        When I verify that running `pro fix CVE-1800-123456` `as non-root` exits `1`
        Then I will see the following on stderr:
        """
        Error: CVE-1800-123456 not found.
        """
        When I verify that running `pro fix USN-12345-12` `as non-root` exits `1`
        Then I will see the following on stderr:
        """
        Error: USN-12345-12 not found.
        """
        When I verify that running `pro fix CVE-12345678-12` `as non-root` exits `1`
        Then I will see the following on stderr:
        """
        Error: issue "CVE-12345678-12" is not recognized.
        Usage: "pro fix CVE-yyyy-nnnn" or "pro fix USN-nnnn"
        """
        When I verify that running `pro fix USN-12345678-12` `as non-root` exits `1`
        Then I will see the following on stderr:
        """
        Error: issue "USN-12345678-12" is not recognized.
        Usage: "pro fix CVE-yyyy-nnnn" or "pro fix USN-nnnn"
        """
        When I run `apt install -y libawl-php=0.60-1 --allow-downgrades` with sudo
        And I run `pro fix USN-4539-1` with sudo
        Then stdout matches regexp:
        """
        USN-4539-1: AWL vulnerability
        Found CVEs:
         - https://ubuntu.com/security/CVE-2020-11728

        Fixing requested USN-4539-1
        1 affected source package is installed: awl
        \(1/1\) awl:
        A fix is available in Ubuntu standard updates.
        .*\{ apt update && apt install --only-upgrade -y libawl-php \}.*

        .*✔.* USN-4539-1 is resolved.
        """
        When I run `pro fix CVE-2020-28196` as non-root
        Then stdout matches regexp:
        """
        CVE-2020-28196: Kerberos vulnerability
         - https://ubuntu.com/security/CVE-2020-28196

        1 affected source package is installed: krb5
        \(1/1\) krb5:
        A fix is available in Ubuntu standard updates.
        The update is already installed.

        .*✔.* CVE-2020-28196 is resolved.
        """
        When I run `pro fix CVE-2022-24959` as non-root
        Then stdout matches regexp:
        """
        CVE-2022-24959: Linux kernel vulnerabilities
         - https://ubuntu.com/security/CVE-2022-24959

        No affected source packages are installed.

        .*✔.* CVE-2022-24959 does not affect your system.
        """
        When I run `apt install -y rsync=3.1.3-8 --allow-downgrades` with sudo
        And I run `apt install -y zlib1g=1:1.2.11.dfsg-2ubuntu1 --allow-downgrades` with sudo
        And I run `pro fix USN-5573-1` with sudo
        Then stdout matches regexp:
        """
        USN-5573-1: rsync vulnerability
        Found CVEs:
         - https://ubuntu.com/security/CVE-2022-37434

        Fixing requested USN-5573-1
        1 affected source package is installed: rsync
        \(1/1\) rsync:
        A fix is available in Ubuntu standard updates.
        .*\{ apt update && apt install --only-upgrade -y rsync \}.*

        .*✔.* USN-5573-1 is resolved.

        Found related USNs:
        - USN-5570-1
        - USN-5570-2

        Fixing related USNs:
        - USN-5570-1
        No affected source packages are installed.

        .*✔.* USN-5570-1 does not affect your system.

        - USN-5570-2
        1 affected source package is installed: zlib
        \(1/1\) zlib:
        A fix is available in Ubuntu standard updates.
        .*\{ apt update && apt install --only-upgrade -y zlib1g \}.*

        .*✔.* USN-5570-2 is resolved.

        Summary:
        .*✔.* USN-5573-1 \[requested\] is resolved.
        .*✔.* USN-5570-1 \[related\] does not affect your system.
        .*✔.* USN-5570-2 \[related\] is resolved.
        """
        When I run `pro fix USN-5573-1` with sudo
        Then stdout matches regexp:
        """
        USN-5573-1: rsync vulnerability
        Found CVEs:
         - https://ubuntu.com/security/CVE-2022-37434

        Fixing requested USN-5573-1
        1 affected source package is installed: rsync
        \(1/1\) rsync:
        A fix is available in Ubuntu standard updates.
        The update is already installed.

        .*✔.* USN-5573-1 is resolved.

        Found related USNs:
        - USN-5570-1
        - USN-5570-2

        Fixing related USNs:
        - USN-5570-1
        No affected source packages are installed.

        .*✔.* USN-5570-1 does not affect your system.

        - USN-5570-2
        1 affected source package is installed: zlib
        \(1/1\) zlib:
        A fix is available in Ubuntu standard updates.
        The update is already installed.

        .*✔.* USN-5570-2 is resolved.

        Summary:
        .*✔.* USN-5573-1 \[requested\] is resolved.
        .*✔.* USN-5570-1 \[related\] does not affect your system.
        .*✔.* USN-5570-2 \[related\] is resolved.
        """
        When I run `pro fix USN-5573-1 --no-related` with sudo
        Then stdout matches regexp:
        """
        USN-5573-1: rsync vulnerability
        Found CVEs:
         - https://ubuntu.com/security/CVE-2022-37434

        Fixing requested USN-5573-1
        1 affected source package is installed: rsync
        \(1/1\) rsync:
        A fix is available in Ubuntu standard updates.
        The update is already installed.

        .*✔.* USN-5573-1 is resolved.
        """

        Examples: ubuntu release details
           | release |
           | focal   |

    @series.xenial
    @uses.config.contract_token
    @uses.config.machine_type.lxd.container
    Scenario Outline: Fix command on an unattached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get update` with sudo
        When I run `apt install -y libawl-php` with sudo
        And I reboot the machine
        And I run `pro fix USN-4539-1` as non-root
        Then stdout matches regexp:
        """
        USN-4539-1: AWL vulnerability
        Found CVEs:
         - https://ubuntu.com/security/CVE-2020-11728

        Fixing requested USN-4539-1
        No affected source packages are installed.

        .*✔.* USN-4539-1 does not affect your system.
        """
        When I run `pro fix CVE-2020-15180` as non-root
        Then stdout matches regexp:
        """
        CVE-2020-15180: MariaDB vulnerabilities
         - https://ubuntu.com/security/CVE-2020-15180

        No affected source packages are installed.

        .*✔.* CVE-2020-15180 does not affect your system.
        """
        When I run `pro fix CVE-2020-28196` as non-root
        Then stdout matches regexp:
        """
        CVE-2020-28196: Kerberos vulnerability
         - https://ubuntu.com/security/CVE-2020-28196

        1 affected source package is installed: krb5
        \(1/1\) krb5:
        A fix is available in Ubuntu standard updates.
        The update is already installed.

        .*✔.* CVE-2020-28196 is resolved.
        """
        When I run `DEBIAN_FRONTEND=noninteractive apt-get install -y expat=2.1.0-7 swish-e matanza ghostscript` with sudo
        And I verify that running `pro fix CVE-2017-9233 --dry-run` `as non-root` exits `1`
        Then stdout matches regexp:
        """
        .*WARNING: The option --dry-run is being used.
        No packages will be installed when running this command..*
        CVE-2017-9233: Coin3D vulnerability
         - https://ubuntu.com/security/CVE-2017-9233

        3 affected source packages are installed: expat, matanza, swish-e
        \(1/3, 2/3\) matanza, swish-e:
        Ubuntu security engineers are investigating this issue.
        \(3/3\) expat:
        A fix is available in Ubuntu standard updates.
        .*\{ apt update && apt install --only-upgrade -y expat \}.*

        2 packages are still affected: matanza, swish-e
        .*✘.* CVE-2017-9233 is not resolved.
        """
        When I verify that running `pro fix CVE-2017-9233` `with sudo` exits `1`
        Then stdout matches regexp:
        """
        CVE-2017-9233: Coin3D vulnerability
         - https://ubuntu.com/security/CVE-2017-9233

        3 affected source packages are installed: expat, matanza, swish-e
        \(1/3, 2/3\) matanza, swish-e:
        Ubuntu security engineers are investigating this issue.
        \(3/3\) expat:
        A fix is available in Ubuntu standard updates.
        .*\{ apt update && apt install --only-upgrade -y expat \}.*

        2 packages are still affected: matanza, swish-e
        .*✘.* CVE-2017-9233 is not resolved.
        """
        When I run `pro fix USN-5079-2 --dry-run` as non-root
        Then stdout matches regexp:
        """
        .*WARNING: The option --dry-run is being used.
        No packages will be installed when running this command..*
        USN-5079-2: curl vulnerabilities
        Found CVEs:
         - https://ubuntu.com/security/CVE-2021-22946
         - https://ubuntu.com/security/CVE-2021-22947

        Fixing requested USN-5079-2
        1 affected source package is installed: curl
        \(1/1\) curl:
        A fix is available in Ubuntu Pro: ESM Infra.

        .*The machine is not attached to an Ubuntu Pro subscription.
        To proceed with the fix, a prompt would ask for a valid Ubuntu Pro token.
        \{ pro attach TOKEN \}.*

        .*Ubuntu Pro service: esm-infra is not enabled.
        To proceed with the fix, a prompt would ask permission to automatically enable
        this service.
        \{ pro enable esm-infra \}.*
        .*\{ apt update && apt install --only-upgrade -y curl libcurl3-gnutls \}.*

        .*✔.* USN-5079-2 is resolved.

        Found related USNs:
        - USN-5079-1

        Fixing related USNs:
        - USN-5079-1
        No affected source packages are installed.

        .*✔.* USN-5079-1 does not affect your system.

        Summary:
        .*✔.* USN-5079-2 \[requested\] is resolved.
        .*✔.* USN-5079-1 \[related\] does not affect your system.
        """
        When I fix `USN-5079-2` by attaching to a subscription with `contract_token_staging_expired`
        Then stdout matches regexp
        """
        USN-5079-2: curl vulnerabilities
        Found CVEs:
         - https://ubuntu.com/security/CVE-2021-22946
         - https://ubuntu.com/security/CVE-2021-22947

        Fixing requested USN-5079-2
        1 affected source package is installed: curl
        \(1/1\) curl:
        A fix is available in Ubuntu Pro: ESM Infra.
        The update is not installed because this system is not attached to a
        subscription.

        Choose: \[S\]ubscribe at ubuntu.com \[A\]ttach existing token \[C\]ancel
        > Enter your token \(from https://ubuntu.com/pro\) to attach this system:
        > .*\{ pro attach .*\}.*
        Attach denied:
        Contract ".*" expired on .*
        Visit https://ubuntu.com/pro to manage contract tokens.

        1 package is still affected: curl
        .*✘.* USN-5079-2 is not resolved.
        """
        When I fix `USN-5079-2` by attaching to a subscription with `contract_token`
        Then stdout matches regexp:
        """
        USN-5079-2: curl vulnerabilities
        Found CVEs:
         - https://ubuntu.com/security/CVE-2021-22946
         - https://ubuntu.com/security/CVE-2021-22947

        Fixing requested USN-5079-2
        1 affected source package is installed: curl
        \(1/1\) curl:
        A fix is available in Ubuntu Pro: ESM Infra.
        The update is not installed because this system is not attached to a
        subscription.

        Choose: \[S\]ubscribe at ubuntu.com \[A\]ttach existing token \[C\]ancel
        > Enter your token \(from https://ubuntu.com/pro\) to attach this system:
        > .*\{ pro attach .*\}.*
        Updating package lists
        Ubuntu Pro: ESM Apps enabled
        Updating package lists
        Ubuntu Pro: ESM Infra enabled
        """
        And stdout matches regexp:
        """
        .*\{ apt update && apt install --only-upgrade -y curl libcurl3-gnutls \}.*

        .*✔.* USN-5079-2 is resolved.

        Found related USNs:
        - USN-5079-1

        Fixing related USNs:
        - USN-5079-1
        No affected source packages are installed.

        .*✔.* USN-5079-1 does not affect your system.

        Summary:
        .*✔.* USN-5079-2 \[requested\] is resolved.
        .*✔.* USN-5079-1 \[related\] does not affect your system.
        """
        When I verify that running `pro fix USN-5051-2` `with sudo` exits `2`
        Then stdout matches regexp:
        """
        USN-5051-2: OpenSSL vulnerability
        Found CVEs:
         - https://ubuntu.com/security/CVE-2021-3712

        Fixing requested USN-5051-2
        1 affected source package is installed: openssl
        \(1/1\) openssl:
        A fix is available in Ubuntu Pro: ESM Infra.
        .*\{ apt update && apt install --only-upgrade -y libssl1.0.0 openssl \}.*

        A reboot is required to complete fix operation.
        .*✘.* USN-5051-2 is not resolved.
        """
        When I run `pro disable esm-infra` with sudo
        # Allow esm-cache to be populated
        And I run `sleep 5` as non-root
        And I run `apt-get install gzip -y` with sudo
        And I run `pro fix USN-5378-4 --dry-run` as non-root
        Then stdout matches regexp:
        """
        .*WARNING: The option --dry-run is being used.
        No packages will be installed when running this command..*
        USN-5378-4: Gzip vulnerability
        Found CVEs:
         - https://ubuntu.com/security/CVE-2022-1271

        Fixing requested USN-5378-4
        1 affected source package is installed: gzip
        \(1/1\) gzip:
        A fix is available in Ubuntu Pro: ESM Infra.

        .*Ubuntu Pro service: esm-infra is not enabled.
        To proceed with the fix, a prompt would ask permission to automatically enable
        this service.
        \{ pro enable esm-infra \}.*
        .*\{ apt update && apt install --only-upgrade -y gzip \}.*

        .*✔.* USN-5378-4 is resolved.

        Found related USNs:
        - USN-5378-1
        - USN-5378-2
        - USN-5378-3

        Fixing related USNs:
        - USN-5378-1
        No affected source packages are installed.

        .*✔.* USN-5378-1 does not affect your system.

        - USN-5378-2
        No affected source packages are installed.

        .*✔.* USN-5378-2 does not affect your system.

        - USN-5378-3
        1 affected source package is installed: xz-utils
        \(1/1\) xz-utils:
        A fix is available in Ubuntu Pro: ESM Infra.

        .*Ubuntu Pro service: esm-infra is not enabled.
        To proceed with the fix, a prompt would ask permission to automatically enable
        this service.
        \{ pro enable esm-infra \}.*
        .*\{ apt update && apt install --only-upgrade -y liblzma5 xz-utils \}.*

        .*✔.* USN-5378-3 is resolved.

        Summary:
        .*✔.* USN-5378-4 \[requested\] is resolved.
        .*✔.* USN-5378-1 \[related\] does not affect your system.
        .*✔.* USN-5378-2 \[related\] does not affect your system.
        .*✔.* USN-5378-3 \[related\] is resolved.
        """
        When I run `pro fix USN-5378-4` `with sudo` and stdin `E`
        Then stdout matches regexp:
        """
        USN-5378-4: Gzip vulnerability
        Found CVEs:
         - https://ubuntu.com/security/CVE-2022-1271

        Fixing requested USN-5378-4
        1 affected source package is installed: gzip
        \(1/1\) gzip:
        A fix is available in Ubuntu Pro: ESM Infra.
        The update is not installed because this system does not have
        esm-infra enabled.

        Choose: \[E\]nable esm-infra \[C\]ancel
        > .*\{ pro enable esm-infra \}.*
        One moment, checking your subscription first
        Updating package lists
        Ubuntu Pro: ESM Infra enabled
        .*\{ apt update && apt install --only-upgrade -y gzip \}.*

        .*✔.* USN-5378-4 is resolved.

        Found related USNs:
        - USN-5378-1
        - USN-5378-2
        - USN-5378-3

        Fixing related USNs:
        - USN-5378-1
        No affected source packages are installed.

        .*✔.* USN-5378-1 does not affect your system.

        - USN-5378-2
        No affected source packages are installed.

        .*✔.* USN-5378-2 does not affect your system.

        - USN-5378-3
        1 affected source package is installed: xz-utils
        \(1/1\) xz-utils:
        A fix is available in Ubuntu Pro: ESM Infra.
        .*\{ apt update && apt install --only-upgrade -y liblzma5 xz-utils \}.*

        .*✔.* USN-5378-3 is resolved.

        Summary:
        .*✔.* USN-5378-4 \[requested\] is resolved.
        .*✔.* USN-5378-1 \[related\] does not affect your system.
        .*✔.* USN-5378-2 \[related\] does not affect your system.
        .*✔.* USN-5378-3 \[related\] is resolved.
        """

        Examples: ubuntu release details
           | release |
           | xenial  |

    @series.bionic
    @uses.config.machine_type.lxd.container
    Scenario: Fix command on an unattached machine
        Given a `bionic` machine with ubuntu-advantage-tools installed
        When I run `apt-get update` with sudo
        When I verify that running `pro fix CVE-1800-123456` `as non-root` exits `1`
        Then I will see the following on stderr:
        """
        Error: CVE-1800-123456 not found.
        """
        When I verify that running `pro fix USN-12345-12` `as non-root` exits `1`
        Then I will see the following on stderr:
        """
        Error: USN-12345-12 not found.
        """
        When I verify that running `pro fix CVE-12345678-12` `as non-root` exits `1`
        Then I will see the following on stderr:
        """
        Error: issue "CVE-12345678-12" is not recognized.
        Usage: "pro fix CVE-yyyy-nnnn" or "pro fix USN-nnnn"
        """
        When I verify that running `pro fix USN-12345678-12` `as non-root` exits `1`
        Then I will see the following on stderr:
        """
        Error: issue "USN-12345678-12" is not recognized.
        Usage: "pro fix CVE-yyyy-nnnn" or "pro fix USN-nnnn"
        """
        When I run `apt install -y libawl-php` with sudo
        And I run `pro fix USN-4539-1 --dry-run` as non-root
        Then stdout matches regexp:
        """
        .*WARNING: The option --dry-run is being used.
        No packages will be installed when running this command..*
        USN-4539-1: AWL vulnerability
        Found CVEs:
         - https://ubuntu.com/security/CVE-2020-11728

        Fixing requested USN-4539-1
        No affected source packages are installed.

        .*✔.* USN-4539-1 does not affect your system.
        """
        When I run `pro fix USN-4539-1` as non-root
        Then stdout matches regexp:
        """
        USN-4539-1: AWL vulnerability
        Found CVEs:
         - https://ubuntu.com/security/CVE-2020-11728

        Fixing requested USN-4539-1
        No affected source packages are installed.

        .*✔.* USN-4539-1 does not affect your system.
        """
        When I run `pro fix CVE-2020-28196` as non-root
        Then stdout matches regexp:
        """
        CVE-2020-28196: Kerberos vulnerability
         - https://ubuntu.com/security/CVE-2020-28196

        1 affected source package is installed: krb5
        \(1/1\) krb5:
        A fix is available in Ubuntu standard updates.
        The update is already installed.

        .*✔.* CVE-2020-28196 is resolved.
        """
        When I run `apt-get install xterm=330-1ubuntu2 -y` with sudo
        And I verify that running `pro fix CVE-2021-27135` `as non-root` exits `1`
        Then stdout matches regexp:
        """
        CVE-2021-27135: xterm vulnerability
         - https://ubuntu.com/security/CVE-2021-27135

        1 affected source package is installed: xterm
        \(1/1\) xterm:
        A fix is available in Ubuntu standard updates.
        Package fixes cannot be installed.
        To install them, run this command as root \(try using sudo\)

        1 package is still affected: xterm
        .*✘.* CVE-2021-27135 is not resolved.
        """
        When I run `pro fix CVE-2021-27135 --dry-run` with sudo
        Then stdout matches regexp:
        """
        .*WARNING: The option --dry-run is being used.
        No packages will be installed when running this command..*
        CVE-2021-27135: xterm vulnerability
         - https://ubuntu.com/security/CVE-2021-27135

        1 affected source package is installed: xterm
        \(1/1\) xterm:
        A fix is available in Ubuntu standard updates.
        .*\{ apt update && apt install --only-upgrade -y xterm \}.*

        .*✔.* CVE-2021-27135 is resolved.
        """
        When I run `pro fix CVE-2021-27135` with sudo
        Then stdout matches regexp:
        """
        CVE-2021-27135: xterm vulnerability
         - https://ubuntu.com/security/CVE-2021-27135

        1 affected source package is installed: xterm
        \(1/1\) xterm:
        A fix is available in Ubuntu standard updates.
        .*\{ apt update && apt install --only-upgrade -y xterm \}.*

        .*✔.* CVE-2021-27135 is resolved.
        """
        When I run `pro fix CVE-2021-27135` with sudo
        Then stdout matches regexp:
        """
        CVE-2021-27135: xterm vulnerability
         - https://ubuntu.com/security/CVE-2021-27135

        1 affected source package is installed: xterm
        \(1/1\) xterm:
        A fix is available in Ubuntu standard updates.
        The update is already installed.

        .*✔.* CVE-2021-27135 is resolved.
        """
        When I run `apt-get install libbz2-1.0=1.0.6-8.1 -y --allow-downgrades` with sudo
        And I run `apt-get install bzip2=1.0.6-8.1 -y` with sudo
        And I run `pro fix USN-4038-3` with sudo
        Then stdout matches regexp:
        """
        USN-4038-3: bzip2 regression
        Found Launchpad bugs:
         - https://launchpad.net/bugs/1834494

        Fixing requested USN-4038-3
        1 affected source package is installed: bzip2
        \(1/1\) bzip2:
        A fix is available in Ubuntu standard updates.
        .*\{ apt update && apt install --only-upgrade -y bzip2 libbz2-1.0 \}.*

        .*✔.* USN-4038-3 is resolved.
        """

    @series.bionic
    @uses.config.machine_type.lxd.container
    Scenario: Fix command on a machine without security/updates source lists
        Given a `bionic` machine with ubuntu-advantage-tools installed
        When I run `sed -i "/bionic-updates/d" /etc/apt/sources.list` with sudo
        And I run `sed -i "/bionic-security/d" /etc/apt/sources.list` with sudo
        And I run `apt-get update` with sudo
        And I run `wget -O pkg.deb https://launchpad.net/ubuntu/+source/openssl/1.1.1-1ubuntu2.1~18.04.14/+build/22454675/+files/openssl_1.1.1-1ubuntu2.1~18.04.14_amd64.deb` as non-root
        And I run `dpkg -i pkg.deb` with sudo
        And I verify that running `pro fix CVE-2023-0286` `as non-root` exits `1`
        Then stdout matches regexp:
        """
        CVE-2023-0286: OpenSSL vulnerabilities
         - https://ubuntu.com/security/CVE-2023-0286

        2 affected source packages are installed: openssl, openssl1.0
        \(1/2, 2/2\) openssl, openssl1.0:
        A fix is available in Ubuntu standard updates.
        - Cannot install package openssl version 1.1.1-1ubuntu2.1~18.04.21

        1 package is still affected: openssl
        .*✘.* CVE-2023-0286 is not resolved.
        """
