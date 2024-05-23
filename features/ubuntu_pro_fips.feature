Feature: Command behaviour when auto-attached in an ubuntu PRO fips image

  Scenario Outline: Check fips is enabled correctly on Ubuntu pro fips Azure machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
      """
      contract_url: 'https://contracts.canonical.com'
      log_level: debug
      features:
        allow_xenial_fips_on_cloud: true
      """
    And I run `pro auto-attach` with sudo
    And I run `pro status --wait` as non-root
    Then I verify that `esm-apps` is enabled
    And I verify that `esm-infra` is enabled
    And I verify that `fips` is enabled
    And I verify that `fips-updates` is disabled
    And I ensure apt update runs without errors
    And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
    When I run `uname -r` as non-root
    Then stdout matches regexp:
      """
      <fips-kernel-version>
      """
    When I run `apt-cache policy <fips-package>` as non-root
    Then stdout does not match regexp:
      """
      .*Installed: \(none\)
      """
    When I run `cat /proc/sys/crypto/fips_enabled` with sudo
    Then I will see the following on stdout:
      """
      1
      """
    When I run `systemctl daemon-reload` with sudo
    When I run `systemctl start ua-auto-attach.service` with sudo
    And I verify that running `systemctl status ua-auto-attach.service` `as non-root` exits `0,3`
    Then stdout matches regexp:
      """
      .*status=0\/SUCCESS.*
      """
    And stdout matches regexp:
      """
      Active: inactive \(dead\).*
      \s*Condition: start condition failed.*
      .*ConditionPathExists=!/var/lib/ubuntu-advantage/private/machine-token.json was not met
      """
    When I verify that running `pro auto-attach` `with sudo` exits `2`
    Then stderr matches regexp:
      """
      This machine is already attached to '.*'
      To use a different subscription first run: sudo pro detach.
      """
    When I run `apt-cache policy` with sudo
    Then apt-cache policy for the following url has priority `510`
      """
      https://esm.ubuntu.com/infra/ubuntu <release>-infra-updates/main amd64 Packages
      """
    And apt-cache policy for the following url has priority `510`
      """
      https://esm.ubuntu.com/infra/ubuntu <release>-infra-security/main amd64 Packages
      """
    And apt-cache policy for the following url has priority `510`
      """
      https://esm.ubuntu.com/apps/ubuntu <release>-apps-updates/main amd64 Packages
      """
    And apt-cache policy for the following url has priority `510`
      """
      https://esm.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
      """
    And apt-cache policy for the following url has priority `1001`
      """
      <fips-apt-source> amd64 Packages
      """
    And I ensure apt update runs without errors
    When I apt install `<infra-pkg>/<release>-infra-security`
    And I run `apt-cache policy <infra-pkg>` as non-root
    Then stdout matches regexp:
      """
      \s*510 https://esm.ubuntu.com/infra/ubuntu <release>-infra-security/main amd64 Packages
      """
    Then stdout matches regexp:
      """
      \s*510 https://esm.ubuntu.com/infra/ubuntu <release>-infra-updates/main amd64 Packages
      """
    And stdout matches regexp:
      """
      Installed: .*[~+]esm
      """
    When I apt install `<apps-pkg>/<release>-apps-security`
    And I run `apt-cache policy <apps-pkg>` as non-root
    Then stdout matches regexp:
      """
      \s*\*\*\* .* 510
      \s*510 https://esm.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
      """
    When I run `pro enable fips-updates --assume-yes` with sudo
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Disabling incompatible service: FIPS
      Removing APT access to FIPS
      Updating package lists
      Configuring APT access to FIPS Updates
      Updating FIPS Updates package lists
      Updating standard Ubuntu package lists
      Installing FIPS Updates packages
      FIPS Updates enabled
      A reboot is required to complete install.
      """
    Then I verify that `fips-updates` is enabled
    When I run `pro status` with sudo
    Then stdout matches regexp:
      """
      NOTICES
      FIPS support requires system reboot to complete configuration.
      """
    When I reboot the machine
    And I run `uname -r` as non-root
    Then stdout matches regexp:
      """
      <fips-kernel-version>
      """
    When I run `apt-cache policy <fips-package>` as non-root
    Then stdout does not match regexp:
      """
      .*Installed: \(none\)
      """
    When I run `cat /proc/sys/crypto/fips_enabled` with sudo
    Then I will see the following on stdout:
      """
      1
      """
    When I run `pro status` with sudo
    Then stdout does not match regexp:
      """
      NOTICES
      FIPS support requires system reboot to complete configuration.
      """

    Examples: ubuntu release
      | release | machine_type   | infra-pkg | apps-pkg | fips-apt-source                                | fips-kernel-version | fips-package      |
      | xenial  | azure.pro-fips | libkrad0  | jq       | https://esm.ubuntu.com/fips/ubuntu xenial/main | fips                | ubuntu-fips       |
      | xenial  | aws.pro-fips   | libkrad0  | jq       | https://esm.ubuntu.com/fips/ubuntu xenial/main | fips                | ubuntu-fips       |
      | bionic  | azure.pro-fips | libkrad0  | bundler  | https://esm.ubuntu.com/fips/ubuntu bionic/main | azure-fips          | ubuntu-azure-fips |
      | bionic  | aws.pro-fips   | libkrad0  | bundler  | https://esm.ubuntu.com/fips/ubuntu bionic/main | aws-fips            | ubuntu-aws-fips   |
      | bionic  | gcp.pro-fips   | libkrad0  | bundler  | https://esm.ubuntu.com/fips/ubuntu bionic/main | gcp-fips            | ubuntu-gcp-fips   |
      | focal   | azure.pro-fips | hello     | 389-ds   | https://esm.ubuntu.com/fips/ubuntu focal/main  | azure-fips          | ubuntu-azure-fips |
      | focal   | aws.pro-fips   | hello     | 389-ds   | https://esm.ubuntu.com/fips/ubuntu focal/main  | aws-fips            | ubuntu-aws-fips   |
      | focal   | gcp.pro-fips   | hello     | 389-ds   | https://esm.ubuntu.com/fips/ubuntu focal/main  | gcp-fips            | ubuntu-gcp-fips   |

  Scenario Outline: Check fips packages are correctly installed on Azure Focal machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
      """
      contract_url: 'https://contracts.canonical.com'
      log_level: debug
      """
    And I run `pro auto-attach` with sudo
    And I run `pro status --wait` as non-root
    Then I verify that `esm-apps` is enabled
    And I verify that `esm-infra` is enabled
    And I verify that `fips` is enabled
    And I verify that `fips-updates` is disabled
    And I ensure apt update runs without errors
    And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
    And I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
    And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
    And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
    And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`

    Examples: ubuntu release
      | release | machine_type   | fips-apt-source                               |
      | focal   | azure.pro-fips | https://esm.ubuntu.com/fips/ubuntu focal/main |
      | focal   | aws.pro-fips   | https://esm.ubuntu.com/fips/ubuntu focal/main |
      | focal   | gcp.pro-fips   | https://esm.ubuntu.com/fips/ubuntu focal/main |

  Scenario Outline: Check fips packages are correctly installed on Azure Bionic & Xenial machines
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
      """
      contract_url: 'https://contracts.canonical.com'
      data_dir: /var/lib/ubuntu-advantage
      log_level: debug
      log_file: /var/log/ubuntu-advantage.log
      features:
        allow_xenial_fips_on_cloud: true
      """
    And I run `pro auto-attach` with sudo
    And I run `pro status --wait` as non-root
    Then I verify that `esm-apps` is enabled
    And I verify that `esm-infra` is enabled
    And I verify that `fips` is enabled
    And I verify that `fips-updates` is disabled
    And I ensure apt update runs without errors
    And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
    And I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
    And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
    And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
    And I verify that `openssh-server-hmac` is installed from apt source `<fips-apt-source>`
    And I verify that `openssh-client-hmac` is installed from apt source `<fips-apt-source>`
    And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`

    Examples: ubuntu release
      | release | machine_type   | fips-apt-source                                |
      | xenial  | azure.pro-fips | https://esm.ubuntu.com/fips/ubuntu xenial/main |
      | xenial  | aws.pro-fips   | https://esm.ubuntu.com/fips/ubuntu xenial/main |
      | bionic  | azure.pro-fips | https://esm.ubuntu.com/fips/ubuntu bionic/main |
      | bionic  | aws.pro-fips   | https://esm.ubuntu.com/fips/ubuntu bionic/main |
      | bionic  | gcp.pro-fips   | https://esm.ubuntu.com/fips/ubuntu bionic/main |

  Scenario Outline: Check fips-updates can be enabled in a focal PRO FIPS machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
      """
      contract_url: 'https://contracts.canonical.com'
      log_level: debug
      """
    And I run `pro auto-attach` with sudo
    And I run `pro status --wait` as non-root
    Then I verify that `fips` is enabled
    And I verify that `fips-updates` is disabled
    When I run `pro enable fips-updates --assume-yes` with sudo
    Then stdout contains substring:
      """
      One moment, checking your subscription first
      Disabling incompatible service: FIPS
      Updating FIPS Updates package lists
      Installing FIPS Updates packages
      Updating standard Ubuntu package lists
      FIPS Updates enabled
      A reboot is required to complete install.
      """
    And I verify that `fips` is disabled
    And I verify that `fips-updates` is enabled
    When I reboot the machine
    And I run `uname -r` as non-root
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
      | release | machine_type   |
      | focal   | aws.pro-fips   |
      | focal   | azure.pro-fips |
      | focal   | gcp.pro-fips   |
