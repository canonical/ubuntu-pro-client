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
      | xenial   | lxd-container |
      | bionic   | lxd-container |
      | focal    | lxd-container |
      | jammy    | lxd-container |
      | noble    | lxd-container |
      | oracular | lxd-container |

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

  @uses.config.contract_token
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
    # Make sure esm cache is empty
    # Technically a folder right, but this works
    When I delete the file `/var/lib/ubuntu-advantage/apt-esm/`
    When I delete the file `/var/lib/apt/periodic/update-success-stamp`
    And I verify that running `pro fix USN-5079-2 --dry-run` `as non-root` exits `1`
    Then stdout matches regexp:
      """
      .*WARNING: The option --dry-run is being used.
      No packages will be installed when running this command..*
      USN-5079-2: curl vulnerabilities
      Associated CVEs:
       - https://ubuntu.com/security/CVE-2021-22946
       - https://ubuntu.com/security/CVE-2021-22947

      Fixing requested USN-5079-2
      1 affected source package is installed: curl

      .*WARNING: Unable to update ESM cache when running as non-root,
      please run sudo apt update and try again if packages cannot be found..*

      \(1/1\) curl:
      A fix is available in Ubuntu Pro: ESM Infra.
      - Cannot install package curl version .*
      - Cannot install package libcurl3-gnutls version .*

      .*The machine is not attached to an Ubuntu Pro subscription.
      To proceed with the fix, a prompt would ask to attach
      the machine to a subscription or use an existing token.
      { pro attach }.*

      .*Ubuntu Pro service: esm-infra is not enabled.
      To proceed with the fix, a prompt would ask permission to automatically enable
      this service.
      { pro enable esm-infra }.*

      1 package is still affected: curl
      .*USN-5079-2 is not resolved.
      """
    When I apt update
    # We just need to await for the esm-cache to be populated
    And I run `sleep 5` as non-root
    And I run `pro fix USN-5079-2 --dry-run` as non-root
    Then stdout matches regexp:
      """
      .*WARNING: The option --dry-run is being used.
      No packages will be installed when running this command..*
      USN-5079-2: curl vulnerabilities
      Associated CVEs:
       - https://ubuntu.com/security/CVE-2021-22946
       - https://ubuntu.com/security/CVE-2021-22947

      Fixing requested USN-5079-2
      1 affected source package is installed: curl
      \(1/1\) curl:
      A fix is available in Ubuntu Pro: ESM Infra.

      .*The machine is not attached to an Ubuntu Pro subscription.
      To proceed with the fix, a prompt would ask to attach
      the machine to a subscription or use an existing token.
      \{ pro attach \}.*

      .*Ubuntu Pro service: esm-infra is not enabled.
      To proceed with the fix, a prompt would ask permission to automatically enable
      this service.
      \{ pro enable esm-infra \}.*
      .*\{ apt update && apt install --only-upgrade -y curl libcurl3-gnutls \}.*

      .*USN-5079-2 is resolved.

      Found related USNs:
      - USN-5079-1

      Fixing related USNs:
      - USN-5079-1
      No affected source packages are installed.

      .*USN-5079-1 does not affect your system.

      Summary:
      .*USN-5079-2 \[requested\] is resolved.
      .*USN-5079-1 \[related\] does not affect your system.
      """
    When I apt install `libawl-php`
    And I reboot the machine
    And I run `pro fix USN-4539-1` as non-root
    Then stdout matches regexp:
      """
      USN-4539-1: AWL vulnerability
      Associated CVEs:
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
    When I apt install `expat=2.1.0-7 swish-e matanza ghostscript`
    And I verify that running `pro fix CVE-2017-9233 --dry-run` `as non-root` exits `1`
    Then stdout matches regexp:
      """
      .*WARNING: The option --dry-run is being used.
      No packages will be installed when running this command..*
      CVE-2017-9233: Expat vulnerability
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
      CVE-2017-9233: Expat vulnerability
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
    When I fix `USN-5079-2` by attaching to a subscription with `contract_token_staging_expired`
    Then stdout matches regexp
      """
      USN-5079-2: curl vulnerabilities
      Associated CVEs:
       - https://ubuntu.com/security/CVE-2021-22946
       - https://ubuntu.com/security/CVE-2021-22947

      Fixing requested USN-5079-2
      1 affected source package is installed: curl
      \(1/1\) curl:
      A fix is available in Ubuntu Pro: ESM Infra.
      The update is not installed because this system is not attached to a
      subscription.

      Choose: \[S\]ubscribe at https://ubuntu.com/pro/subscribe \[A\]ttach existing token \[C\]ancel
      > Enter your token \(from https://ubuntu.com/pro/dashboard\) to attach this system:
      > .*\{ pro attach .*\}.*
      Attach denied:
      Contract ".*" expired on .*
      Visit https://ubuntu.com/pro/dashboard to manage contract tokens.

      1 package is still affected: curl
      .*✘.* USN-5079-2 is not resolved.
      """
    When I fix `USN-5079-2` by attaching to a subscription with `contract_token`
    Then stdout matches regexp:
      """
      USN-5079-2: curl vulnerabilities
      Associated CVEs:
       - https://ubuntu.com/security/CVE-2021-22946
       - https://ubuntu.com/security/CVE-2021-22947

      Fixing requested USN-5079-2
      1 affected source package is installed: curl
      \(1/1\) curl:
      A fix is available in Ubuntu Pro: ESM Infra.
      The update is not installed because this system is not attached to a
      subscription.

      Choose: \[S\]ubscribe at https://ubuntu.com/pro/subscribe \[A\]ttach existing token \[C\]ancel
      > Enter your token \(from https://ubuntu.com/pro/dashboard\) to attach this system:
      > .*\{ pro attach .*\}.*
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
      Associated CVEs:
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
    And I apt install `gzip`
    And I run `pro fix USN-5378-4 --dry-run` as non-root
    Then stdout matches regexp:
      """
      .*WARNING: The option --dry-run is being used.
      No packages will be installed when running this command..*
      USN-5378-4: Gzip vulnerability
      Associated CVEs:
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
      Associated CVEs:
       - https://ubuntu.com/security/CVE-2022-1271

      Fixing requested USN-5378-4
      1 affected source package is installed: gzip
      \(1/1\) gzip:
      A fix is available in Ubuntu Pro: ESM Infra.
      The update is not installed because this system does not have
      esm-infra enabled.

      Choose: \[E\]nable esm-infra \[C\]ancel
      > .*\{ pro enable esm-infra \}.*
      Enabling Ubuntu Pro: ESM Infra
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
    When I run `pro detach --assume-yes` with sudo
    And I run `sed -i "/xenial-updates/d" /etc/apt/sources.list` with sudo
    And I run `sed -i "/xenial-security/d" /etc/apt/sources.list` with sudo
    And I apt update
    And I apt install `squid`
    And I verify that running `pro fix CVE-2020-25097` `as non-root` exits `1`
    Then stdout matches regexp:
      """
      CVE-2020-25097: Squid vulnerabilities
       - https://ubuntu.com/security/CVE-2020-25097

      1 affected source package is installed: squid3
      \(1/1\) squid3:
      A fix is available in Ubuntu standard updates.
      - Cannot install package squid version 3.5.12-1ubuntu7.16
      - Cannot install package squid-common version 3.5.12-1ubuntu7.16

      1 package is still affected: squid3
      .*✘.* CVE-2020-25097 is not resolved
      """

    Examples: ubuntu release details
      | release | machine_type  |
      | xenial  | lxd-container |
      | xenial  | lxd-vm        |

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
      | bionic  | wsl           |
