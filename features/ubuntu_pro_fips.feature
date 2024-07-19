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
    When I run `apt-cache policy <fips-meta>` as non-root
    Then stdout does not match regexp:
      """
      .*Installed: \(none\)
      """
    When I run `cat /proc/sys/crypto/fips_enabled` with sudo
    Then I will see the following on stdout:
      """
      1
      """
    And I verify that `<fips-packages>` are installed from apt source `https://esm.ubuntu.com/fips/ubuntu <release>/main`
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
      https://esm.ubuntu.com/fips/ubuntu <release>/main amd64 Packages
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
    And I verify that `fips-updates` is enabled
    And I verify that `fips` is disabled
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
      | release | machine_type   | infra-pkg | apps-pkg | fips-kernel-version | fips-meta         | fips-packages                                                                                    |
      | xenial  | azure.pro-fips | libkrad0  | jq       | fips                | ubuntu-fips       | openssh-server openssh-client strongswan openssh-server-hmac openssh-client-hmac strongswan-hmac |
      | xenial  | aws.pro-fips   | libkrad0  | jq       | fips                | ubuntu-fips       | openssh-server openssh-client strongswan openssh-server-hmac openssh-client-hmac strongswan-hmac |
      | bionic  | azure.pro-fips | libkrad0  | bundler  | azure-fips          | ubuntu-azure-fips | openssh-server openssh-client strongswan openssh-server-hmac openssh-client-hmac strongswan-hmac |
      | bionic  | aws.pro-fips   | libkrad0  | bundler  | aws-fips            | ubuntu-aws-fips   | openssh-server openssh-client strongswan openssh-server-hmac openssh-client-hmac strongswan-hmac |
      | bionic  | gcp.pro-fips   | libkrad0  | bundler  | gcp-fips            | ubuntu-gcp-fips   | openssh-server openssh-client strongswan openssh-server-hmac openssh-client-hmac strongswan-hmac |
      | focal   | azure.pro-fips | hello     | 389-ds   | azure-fips          | ubuntu-azure-fips | openssh-server openssh-client strongswan strongswan-hmac                                         |
      | focal   | aws.pro-fips   | hello     | 389-ds   | aws-fips            | ubuntu-aws-fips   | openssh-server openssh-client strongswan strongswan-hmac                                         |
      | focal   | gcp.pro-fips   | hello     | 389-ds   | gcp-fips            | ubuntu-gcp-fips   | openssh-server openssh-client strongswan strongswan-hmac                                         |
