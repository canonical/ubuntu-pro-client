Feature: Ua fix command behaviour

  Scenario Outline: Useful SSL failure message when there aren't any ca-certs
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I apt remove `ca-certificates`
    When I run `rm -f /etc/ssl/certs/ca-certificates.crt` with sudo
    When I verify that running `ua fix CVE-1800-123456` `as non-root` exits `1`
    Then stderr matches regexp:
      """
      Failed to access URL: https://.*
      Cannot verify certificate of server
      Please install "ca-certificates" and try again.
      """
    When I apt install `ca-certificates`
    When I run `mv /etc/ssl/certs /etc/ssl/wronglocation` with sudo
    When I verify that running `pro fix CVE-1800-123456` `as non-root` exits `1`
    Then stderr matches regexp:
      """
      Failed to access URL: https://.*
      Cannot verify certificate of server
      Please check your openssl configuration.
      """

    Examples: ubuntu release
      | release  | machine_type  |
      | bionic   | lxd-container |
      | focal    | lxd-container |
      | jammy    | lxd-container |
      | noble    | lxd-container |
      | questing | lxd-container |
      | resolute | lxd-container |
      | stonking | lxd-container |

  Scenario Outline: Fix command on an unattached machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
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
    When I apt install `libawl-php=0.60-1`
    And I run `pro fix USN-4539-1` with sudo
    Then stdout matches regexp:
      """
      USN-4539-1: AWL vulnerability
      Associated CVEs:
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
    When I apt install `rsync=3.1.3-8 zlib1g=1:1.2.11.dfsg-2ubuntu1`
    And I run `pro fix USN-5573-1` with sudo
    Then stdout matches regexp:
      """
      USN-5573-1: rsync vulnerability
      Associated CVEs:
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
      - USN-6736-1
      - USN-6736-2

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

      - USN-6736-1
      1 affected source package is installed: klibc
      \(1/1\) klibc:
      A fix is available in Ubuntu standard updates.
      The update is already installed.

      .*✔.* USN-6736-1 is resolved.

      - USN-6736-2
      No affected source packages are installed.

      .*✔.* USN-6736-2 does not affect your system.

      Summary:
      .*✔.* USN-5573-1 \[requested\] is resolved.
      .*✔.* USN-5570-1 \[related\] does not affect your system.
      .*✔.* USN-5570-2 \[related\] is resolved.
      .*✔.* USN-6736-1 \[related\] is resolved.
      .*✔.* USN-6736-2 \[related\] does not affect your system.
      """
    When I run `pro fix USN-5573-1` with sudo
    Then stdout matches regexp:
      """
      USN-5573-1: rsync vulnerability
      Associated CVEs:
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
      - USN-6736-1
      - USN-6736-2

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

      - USN-6736-1
      1 affected source package is installed: klibc
      \(1/1\) klibc:
      A fix is available in Ubuntu standard updates.
      The update is already installed.

      .*✔.* USN-6736-1 is resolved.

      - USN-6736-2
      No affected source packages are installed.

      .*✔.* USN-6736-2 does not affect your system.

      Summary:
      .*✔.* USN-5573-1 \[requested\] is resolved.
      .*✔.* USN-5570-1 \[related\] does not affect your system.
      .*✔.* USN-5570-2 \[related\] is resolved.
      .*✔.* USN-6736-1 \[related\] is resolved.
      .*✔.* USN-6736-2 \[related\] does not affect your system.
      """
    When I run `pro fix USN-5573-1 --no-related` with sudo
    Then stdout matches regexp:
      """
      USN-5573-1: rsync vulnerability
      Associated CVEs:
       - https://ubuntu.com/security/CVE-2022-37434

      Fixing requested USN-5573-1
      1 affected source package is installed: rsync
      \(1/1\) rsync:
      A fix is available in Ubuntu standard updates.
      The update is already installed.

      .*✔.* USN-5573-1 is resolved.
      """

    Examples: ubuntu release details
      | release | machine_type  |
      | focal   | lxd-container |
      | focal   | wsl           |

  Scenario Outline: Fix command on an unattached machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
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
    When I apt install `libawl-php`
    And I run `pro fix USN-4539-1 --dry-run` as non-root
    Then stdout matches regexp:
      """
      .*WARNING: The option --dry-run is being used.
      No packages will be installed when running this command..*
      USN-4539-1: AWL vulnerability
      Associated CVEs:
       - https://ubuntu.com/security/CVE-2020-11728

      Fixing requested USN-4539-1
      No affected source packages are installed.

      .*✔.* USN-4539-1 does not affect your system.
      """
    When I run `pro fix USN-4539-1` as non-root
    Then stdout matches regexp:
      """
      USN-4539-1: AWL vulnerability
      Associated CVEs:
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
    When I apt install `xterm=330-1ubuntu2`
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
    When I apt install `libbz2-1.0=1.0.6-8.1 bzip2=1.0.6-8.1`
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
    When I run `pro fix USN-6130-1` as non-root
    Then stdout matches regexp:
      """
      USN-6130-1: Linux kernel vulnerabilities
      Associated CVEs:
       - https://ubuntu.com/security/CVE-2023-30456
       - https://ubuntu.com/security/CVE-2023-1380
       - https://ubuntu.com/security/CVE-2023-32233
       - https://ubuntu.com/security/CVE-2023-31436

      Fixing requested USN-6130-1
      No affected source packages are installed.

      .*✔.* USN-6130-1 does not affect your system.

      Found related USNs:
      - USN-6033-1
      - USN-6122-1
      - USN-6123-1
      - USN-6124-1
      - USN-6127-1
      - USN-6131-1
      - USN-6132-1
      - USN-6135-1
      - USN-6149-1
      - USN-6150-1
      - USN-6162-1
      - USN-6173-1
      - USN-6175-1
      - USN-6186-1
      - USN-6222-1
      - USN-6256-1
      - USN-6385-1
      - USN-6460-1
      - USN-6699-1

      Fixing related USNs:
      - USN-6033-1
      No affected source packages are installed.

      .*✔.* USN-6033-1 does not affect your system.

      - USN-6122-1
      No affected source packages are installed.

      .*✔.* USN-6122-1 does not affect your system.

      - USN-6123-1
      No affected source packages are installed.

      .*✔.* USN-6123-1 does not affect your system.

      - USN-6124-1
      No affected source packages are installed.

      .*✔.* USN-6124-1 does not affect your system.

      - USN-6127-1
      No affected source packages are installed.

      .*✔.* USN-6127-1 does not affect your system.

      - USN-6131-1
      No affected source packages are installed.

      .*✔.* USN-6131-1 does not affect your system.

      - USN-6132-1
      No affected source packages are installed.

      .*✔.* USN-6132-1 does not affect your system.

      - USN-6135-1
      No affected source packages are installed.

      .*✔.* USN-6135-1 does not affect your system.

      - USN-6149-1
      No affected source packages are installed.

      .*✔.* USN-6149-1 does not affect your system.

      - USN-6150-1
      No affected source packages are installed.

      .*✔.* USN-6150-1 does not affect your system.

      - USN-6162-1
      No affected source packages are installed.

      .*✔.* USN-6162-1 does not affect your system.

      - USN-6173-1
      No affected source packages are installed.

      .*✔.* USN-6173-1 does not affect your system.

      - USN-6175-1
      No affected source packages are installed.

      .*✔.* USN-6175-1 does not affect your system.

      - USN-6186-1
      No affected source packages are installed.

      .*✔.* USN-6186-1 does not affect your system.

      - USN-6222-1
      No affected source packages are installed.

      .*✔.* USN-6222-1 does not affect your system.

      - USN-6256-1
      No affected source packages are installed.

      .*✔.* USN-6256-1 does not affect your system.

      - USN-6385-1
      No affected source packages are installed.

      .*✔.* USN-6385-1 does not affect your system.

      - USN-6460-1
      No affected source packages are installed.

      .*✔.* USN-6460-1 does not affect your system.

      - USN-6699-1
      No affected source packages are installed.

      .*✔.* USN-6699-1 does not affect your system.

      Summary:
      .*✔.* USN-6130-1 \[requested\] does not affect your system.
      .*✔.* USN-6033-1 \[related\] does not affect your system.
      .*✔.* USN-6122-1 \[related\] does not affect your system.
      .*✔.* USN-6123-1 \[related\] does not affect your system.
      .*✔.* USN-6124-1 \[related\] does not affect your system.
      .*✔.* USN-6127-1 \[related\] does not affect your system.
      .*✔.* USN-6131-1 \[related\] does not affect your system.
      .*✔.* USN-6132-1 \[related\] does not affect your system.
      .*✔.* USN-6135-1 \[related\] does not affect your system.
      .*✔.* USN-6149-1 \[related\] does not affect your system.
      .*✔.* USN-6150-1 \[related\] does not affect your system.
      .*✔.* USN-6162-1 \[related\] does not affect your system.
      .*✔.* USN-6173-1 \[related\] does not affect your system.
      .*✔.* USN-6175-1 \[related\] does not affect your system.
      .*✔.* USN-6186-1 \[related\] does not affect your system.
      .*✔.* USN-6222-1 \[related\] does not affect your system.
      .*✔.* USN-6256-1 \[related\] does not affect your system.
      .*✔.* USN-6385-1 \[related\] does not affect your system.
      .*✔.* USN-6460-1 \[related\] does not affect your system.
      .*✔.* USN-6699-1 \[related\] does not affect your system.
      """
    When I run `pro fix CVE-2023-42752` with sudo
    Then stdout matches regexp:
      """
      CVE-2023-42752: Linux kernel \(NVIDIA\) vulnerabilities
       - https://ubuntu.com/security/CVE-2023-42752

      No affected source packages are installed.

      .*✔.* CVE-2023-42752 does not affect your system.
      """

    Examples: ubuntu release details
      | release | machine_type  |
      | bionic  | lxd-container |
      | bionic  | wsl           |

  Scenario Outline: Fix command on a machine without security/updates source lists
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `sed -i "/bionic-updates/d" /etc/apt/sources.list` with sudo
    And I run `sed -i "/bionic-security/d" /etc/apt/sources.list` with sudo
    And I apt update
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

    Examples: ubuntu release details
      | release | machine_type  |
      | bionic  | lxd-container |
      | bionic  | lxd-vm        |

  Scenario Outline: Fix command on a machine without security/updates source lists
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `sed -i "/bionic-updates/d" /etc/apt/sources.list` with sudo
    And I run `sed -i "/bionic-security/d" /etc/apt/sources.list` with sudo
    And I apt update
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
      - Cannot install package libssl1.1 version 1.1.1-1ubuntu2.1~18.04.21
      - Cannot install package openssl version 1.1.1-1ubuntu2.1~18.04.21
      - Cannot install package libssl1.0.0 version 1.0.2n-1ubuntu5.11

      2 packages are still affected: openssl, openssl1.0
      .*✘.* CVE-2023-0286 is not resolved.
      """

    Examples: ubuntu release details
      | release | machine_type |
      | bionic  | wsl          |

  Scenario Outline: Fix command on an unattached machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
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
    When I apt install `libawl-php`
    And I run `pro fix USN-4539-1 --dry-run` as non-root
    Then stdout matches regexp:
      """
      .*WARNING: The option --dry-run is being used.
      No packages will be installed when running this command..*
      USN-4539-1: AWL vulnerability
      Associated CVEs:
       - https://ubuntu.com/security/CVE-2020-11728

      Fixing requested USN-4539-1
      No affected source packages are installed.

      .*✔.* USN-4539-1 does not affect your system.
      """
    When I run `pro fix USN-4539-1` as non-root
    Then stdout matches regexp:
      """
      USN-4539-1: AWL vulnerability
      Associated CVEs:
       - https://ubuntu.com/security/CVE-2020-11728

      Fixing requested USN-4539-1
      No affected source packages are installed.

      .*✔.* USN-4539-1 does not affect your system.
      """
    When I run `pro fix CVE-2025-26465` as non-root
    And I remove colors from output
    Then stdout matches regexp:
      """
      CVE-2025-26465: .*OpenSSH.*
       - https://ubuntu.com/security/CVE-2025-26465

      1 affected source package is installed: openssh
      \(1/1\) openssh:
      A fix is available in Ubuntu standard updates.
      The update is already installed.

      .*✔.* CVE-2025-26465 is resolved.
      """
    When I apt install `curl=8.18.0-1ubuntu2 libcurl4t64=8.18.0-1ubuntu2`
    And I verify that running `pro fix CVE-2026-8924` `as non-root` exits `1`
    And I remove colors from output
    Then stdout matches regexp:
      """
      CVE-2026-8924: curl vulnerabilities
       - https://ubuntu.com/security/CVE-2026-8924

      1 affected source package is installed: curl
      \(1/1\) curl:
      A fix is available in Ubuntu standard updates.
      Package fixes cannot be installed.
      To install them, run this command as root \(try using sudo\)

      1 package is still affected: curl
      .*✘.* CVE-2026-8924 is not resolved.
      """
    When I run `pro fix CVE-2026-8924 --dry-run` with sudo
    And I remove colors from output
    Then stdout matches regexp:
      """
      .*WARNING: The option --dry-run is being used.
      No packages will be installed when running this command..*
      CVE-2026-8924: curl vulnerabilities
       - https://ubuntu.com/security/CVE-2026-8924

      1 affected source package is installed: curl
      \(1/1\) curl:
      A fix is available in Ubuntu standard updates.
      .*\{ apt update && apt install --only-upgrade -y curl libcurl4t64 \}.*

      .*✔.* CVE-2026-8924 is resolved.
      """
    When I run `pro fix CVE-2026-8924` with sudo
    And I remove colors from output
    Then stdout matches regexp:
      """
      CVE-2026-8924: curl vulnerabilities
       - https://ubuntu.com/security/CVE-2026-8924

      1 affected source package is installed: curl
      \(1/1\) curl:
      A fix is available in Ubuntu standard updates.
      .*\{ apt update && apt install --only-upgrade -y curl libcurl4t64 \}.*

      .*✔.* CVE-2026-8924 is resolved.
      """
    When I run `pro fix CVE-2026-8924` with sudo
    And I remove colors from output
    Then stdout matches regexp:
      """
      CVE-2026-8924: curl vulnerabilities
       - https://ubuntu.com/security/CVE-2026-8924

      1 affected source package is installed: curl
      \(1/1\) curl:
      A fix is available in Ubuntu standard updates.
      The update is already installed.

      .*✔.* CVE-2026-8924 is resolved.
      """
    When I apt install `wget=1.25.0-2ubuntu4`
    And I run `pro fix USN-8572-1` with sudo
    And I remove colors from output
    Then stdout matches regexp:
      """
      USN-8572-1: Wget vulnerability
      Associated CVEs:
       - https://ubuntu.com/security/CVE-2026-15146

      Fixing requested USN-8572-1
      1 affected source package is installed: wget
      \(1/1\) wget:
      A fix is available in Ubuntu standard updates.
      .*\{ apt update && apt install --only-upgrade -y wget \}.*

      .*✔.* USN-8572-1 is resolved.
      """
    When I run `pro fix USN-8612-1` as non-root
    And I remove colors from output
    Then stdout matches regexp:
      """
      USN-8612-1: Roc Toolkit vulnerability
      Associated CVEs:
       - https://ubuntu.com/security/CVE-2026-29022

      Fixing requested USN-8612-1
      No affected source packages are installed.

      .*✔.* USN-8612-1 does not affect your system.
      """
    When I run `pro fix CVE-2026-46108` with sudo
    And I remove colors from output
    Then stdout matches regexp:
      """
      CVE-2026-46108: .*
       - https://ubuntu.com/security/CVE-2026-46108

      No affected source packages are installed.

      .*✔.* CVE-2026-46108 does not affect your system.
      """

    Examples: ubuntu release details
      | release  | machine_type  |
      | resolute | lxd-container |

  Scenario Outline: Fix command on a machine without security/updates source lists
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `sed -i 's/ resolute-updates//' /etc/apt/sources.list.d/ubuntu.sources` with sudo
    And I run `sed -i '1,/^Signed-By:/!d' /etc/apt/sources.list.d/ubuntu.sources` with sudo
    And I apt update
    And I run `wget -L -O /tmp/curl.deb 'https://launchpad.net/ubuntu/+source/curl/8.18.0-1ubuntu2/+build/32361160/+files/curl_8.18.0-1ubuntu2_amd64.deb'` as non-root
    And I run `wget -L -O /tmp/libcurl4t64.deb 'https://launchpad.net/ubuntu/+source/curl/8.18.0-1ubuntu2/+build/32361160/+files/libcurl4t64_8.18.0-1ubuntu2_amd64.deb'` as non-root
    And I run `dpkg -i /tmp/libcurl4t64.deb /tmp/curl.deb` with sudo
    And I verify that running `pro fix CVE-2026-8924` `as non-root` exits `1`
    Then stdout matches regexp:
      """
      CVE-2026-8924: curl vulnerabilities
       - https://ubuntu.com/security/CVE-2026-8924

      1 affected source package is installed: curl
      \(1/1\) curl:
      A fix is available in Ubuntu standard updates.
      - Cannot install package curl version .*
      - Cannot install package libcurl4t64 version .*

      1 package is still affected: curl
      .*✘.* CVE-2026-8924 is not resolved.
      """

    Examples: ubuntu release details
      | release  | machine_type  |
      | resolute | lxd-container |
