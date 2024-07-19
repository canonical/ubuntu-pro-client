@uses.config.contract_token
Feature: FIPS enablement in lxd VMs

  @slow
  Scenario Outline: Attached enable of FIPS in an ubuntu lxd vm
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I apt install `jq`
    And I run shell command `pro status --format json` with sudo
    And I apply this jq filter `'.services[] | select(.name == "livepatch") | .available'` to the output
    Then I will see the following on stdout
      """
      "yes"
      """
    When I run `pro disable livepatch` with sudo
    And I apt install `openssh-client openssh-server strongswan`
    And I run `pro enable fips` `with sudo` and stdin `y`
    Then stdout matches regexp:
      """
      This will install the FIPS packages. The Livepatch service will be unavailable.
      Warning: This action can take some time and cannot be undone.
      """
    And stdout contains substring:
      """
      Updating FIPS package lists
      Updating standard Ubuntu package lists
      Installing FIPS packages
      FIPS enabled
      A reboot is required to complete install.
      """
    When I run `pro status --all` with sudo
    Then stdout matches regexp:
      """
      FIPS support requires system reboot to complete configuration
      """
    And I ensure apt update runs without errors
    And I verify that `<fips-packages>` are installed from apt source `<fips-apt-source>`
    When I run shell command `pro status --format json --all` with sudo
    And I apply this jq filter `'.services[] | select(.name == "livepatch") | .available'` to the output
    Then I will see the following on stdout
      """
      "no"
      """
    When I run shell command `pro status --format json --all` with sudo
    And I apply this jq filter `'.services[] | select(.name == "livepatch") | .blocked_by[0].reason'` to the output
    Then I will see the following on stdout
      """
      "Livepatch cannot be enabled while running the official FIPS certified kernel. If you would like a FIPS compliant kernel with additional bug fixes and security updates, you can use the FIPS Updates service with Livepatch."
      """
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
    When I run `pro status --all` with sudo
    Then stdout does not match regexp:
      """
      FIPS support requires system reboot to complete configuration
      """
    When I run `pro disable fips` `with sudo` and stdin `y`
    Then stdout matches regexp:
      """
      This will disable the FIPS entitlement but the FIPS packages will remain installed.
      """
    And stdout matches regexp:
      """
      Updating package lists
      A reboot is required to complete disable operation
      """
    When I run `pro status --all` with sudo
    Then stdout matches regexp:
      """
      Disabling FIPS requires system reboot to complete operation
      """
    When I run `apt-cache policy ubuntu-fips` as non-root
    Then stdout matches regexp:
      """
      .*Installed: \(none\)
      """
    When I reboot the machine
    Then I verify that packages `<fips-packages>` installed versions match regexp `fips`
    And I verify that `fips` is disabled
    When I run `pro status --all` with sudo
    Then stdout does not match regexp:
      """
      Disabling FIPS requires system reboot to complete operation
      """
    When I run `pro enable fips --assume-yes --format json --assume-yes` with sudo
    Then stdout is a json matching the `ua_operation` schema
    And I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [], "failed_services": [], "needs_reboot": true, "processed_services": ["fips"], "result": "success", "warnings": []}
      """
    When I reboot the machine
    And I run `pro disable fips --assume-yes --format json` with sudo
    Then stdout is a json matching the `ua_operation` schema
    And I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [], "failed_services": [], "needs_reboot": true, "processed_services": ["fips"], "result": "success", "warnings": []}
      """
    And I verify that `fips` is disabled

    Examples: ubuntu release
      | release | machine_type | fips-apt-source                                | fips-packages                                                                                    |
      | xenial  | lxd-vm       | https://esm.ubuntu.com/fips/ubuntu xenial/main | openssh-server openssh-client strongswan openssh-server-hmac openssh-client-hmac strongswan-hmac |
      | bionic  | lxd-vm       | https://esm.ubuntu.com/fips/ubuntu bionic/main | openssh-server openssh-client strongswan openssh-server-hmac openssh-client-hmac strongswan-hmac |
      | focal   | lxd-vm       | https://esm.ubuntu.com/fips/ubuntu focal/main  | openssh-server openssh-client strongswan strongswan-hmac                                         |

  @slow
  Scenario Outline: Attached enable of FIPS-updates in an ubuntu lxd vm
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I apt install `openssh-client openssh-server strongswan`
    And I run `pro enable fips-updates` `with sudo` and stdin `y`
    Then stdout matches regexp:
      """
      This will install the FIPS packages including security updates.
      Warning: This action can take some time and cannot be undone.
      """
    And stdout contains substring:
      """
      Updating FIPS Updates package lists
      Updating standard Ubuntu package lists
      Installing FIPS Updates packages
      """
    And if `<release>` in `jammy` and stdout matches regexp:
      """
      Installing libcharon-extauth-plugins libstrongswan libstrongswan-standard-plugins openssh-client openssh-server openssh-sftp-server strongswan strongswan-charon strongswan-libcharon strongswan-starter
      """
    And stdout contains substring:
      """
      FIPS Updates enabled
      A reboot is required to complete install.
      """
    And I verify that `fips-updates` is enabled
    And I verify that `livepatch` is enabled
    And I ensure apt update runs without errors
    And I verify that `<fips-packages>` are installed from apt source `https://esm.ubuntu.com/fips-updates/ubuntu <release>-updates/main`
    When I verify that running `pro enable fips --assume-yes` `with sudo` exits `1`
    Then stdout contains substring:
      """
      Cannot enable FIPS when FIPS Updates is enabled
      """
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
    And I verify that `fips-updates` is enabled
    And I verify that `livepatch` is enabled
    When I run `pro disable fips-updates` `with sudo` and stdin `y`
    Then stdout matches regexp:
      """
      This will disable the FIPS Updates entitlement but the FIPS Updates packages will remain installed.
      """
    And stdout matches regexp:
      """
      Updating package lists
      A reboot is required to complete disable operation
      """
    When I reboot the machine
    Then I verify that packages `<fips-packages>` installed versions match regexp `<fips-regex>`
    And I verify that `fips-updates` is disabled
    When I verify that running `pro enable fips --assume-yes` `with sudo` exits `1`
    Then stdout matches regexp:
      """
      Cannot enable FIPS because FIPS Updates was once enabled.
      """
    And I verify that files exist matching `/var/lib/ubuntu-advantage/services-once-enabled`
    When I run `pro enable fips-updates --assume-yes` with sudo
    And I reboot the machine
    Then I verify that `fips-updates` is enabled
    When I run `pro disable livepatch` with sudo
    Then I verify that `livepatch` is disabled
    When I run `pro enable livepatch --assume-yes` with sudo
    Then I verify that `fips-updates` is enabled
    And I verify that `livepatch` is enabled
    When I run `pro disable fips-updates --assume-yes` with sudo
    And I run `pro enable fips-updates --assume-yes --format json --assume-yes` with sudo
    Then stdout is a json matching the `ua_operation` schema
    And I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [], "failed_services": [], "needs_reboot": true, "processed_services": ["fips-updates"], "result": "success", "warnings": []}
      """
    When I reboot the machine
    And I run `pro disable fips-updates --assume-yes --format json` with sudo
    Then stdout is a json matching the `ua_operation` schema
    And I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [], "failed_services": [], "needs_reboot": true, "processed_services": ["fips-updates"], "result": "success", "warnings": []}
      """
    And I verify that `fips-updates` is disabled

    Examples: ubuntu release
      | release | machine_type | fips-packages                                                                                    | fips-regex |
      | xenial  | lxd-vm       | openssh-server openssh-client strongswan openssh-server-hmac openssh-client-hmac strongswan-hmac | fips       |
      | bionic  | lxd-vm       | openssh-server openssh-client strongswan openssh-server-hmac openssh-client-hmac strongswan-hmac | fips       |
      | focal   | lxd-vm       | openssh-server openssh-client strongswan strongswan-hmac                                         | fips       |
      | jammy   | lxd-vm       | openssh-server openssh-client strongswan strongswan-hmac                                         | Fips       |

  @slow
  Scenario Outline: Attached enable fips-updates on fips enabled vm
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I run `pro enable fips --assume-yes` with sudo
    Then stdout contains substring:
      """
      Updating FIPS package lists
      Updating standard Ubuntu package lists
      Installing FIPS packages
      FIPS enabled
      A reboot is required to complete install.
      """
    And I verify that `fips` is enabled
    And I verify that `livepatch` is disabled
    When I reboot the machine
    And I run `uname -r` as non-root
    Then stdout matches regexp:
      """
      fips
      """
    When I verify that running `pro enable fips-updates --assume-yes` `with sudo` exits `0`
    Then stdout contains substring:
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
    When I reboot the machine
    And I run `pro enable livepatch` with sudo
    Then I verify that `fips-updates` is enabled
    And I verify that `fips` is disabled
    And I verify that `livepatch` is enabled
    When I run `pro status --all` with sudo
    Then stdout matches regexp:
      """
      fips +yes +n/a
      """
    When I run `uname -r` as non-root
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
      | release | machine_type |
      | xenial  | lxd-vm       |
      | bionic  | lxd-vm       |
      | focal   | lxd-vm       |

  @slow
  Scenario Outline: FIPS enablement message when cloud init didn't run properly
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I delete the file `/run/cloud-init/instance-data.json`
    And I attach `contract_token` with sudo
    And I run `pro enable fips --assume-yes` with sudo
    Then stdout matches regexp:
      """
      Could not determine cloud, defaulting to generic FIPS package.
      """
    And I verify that `fips` is enabled

    Examples: ubuntu release
      | release | machine_type |
      | xenial  | lxd-vm       |
      | bionic  | lxd-vm       |
      | focal   | lxd-vm       |

  @slow
  Scenario Outline: Attached enable fips-preview
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then I verify that `fips-preview` is disabled
    When I verify that running `pro enable fips-preview` `with sudo` and stdin `N` exits `1`
    Then stdout matches regexp:
      """
      FIPS Preview cannot be enabled with Livepatch.
      """
    When I run `pro disable livepatch` with sudo
    And I verify that running `pro enable fips-preview` `with sudo` and stdin `N` exits `1`
    Then stdout matches regexp:
      """
      This will install crypto packages that have been submitted to NIST for review
      but do not have FIPS certification yet. Use this for early access to the FIPS
      modules.
      Please note that the Livepatch service will be unavailable after
      this operation.
      Warning: This action can take some time and cannot be undone.
      """
    When I run `pro enable realtime-kernel --assume-yes` with sudo
    And I verify that running `pro enable fips-preview` `with sudo` and stdin `N` exits `1`
    Then stdout matches regexp:
      """
      FIPS Preview cannot be enabled with Real-time kernel.
      """

    Examples: ubuntu release
      | release | machine_type |
      | jammy   | lxd-vm       |
