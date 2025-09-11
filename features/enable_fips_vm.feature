@uses.config.contract_token
Feature: FIPS enablement in lxd VMs

  @slow
  Scenario Outline: Attached enable of FIPS in an ubuntu lxd vm
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I run shell command `pro status --format json` with sudo
    And I apply this jq filter `.services[] | select(.name == "fips") | .blocked_by[0].reason_code` to the output
    Then I will see the following on stdout:
      """
      "livepatch-invalidates-fips"
      """
    When I run `pro disable livepatch` with sudo
    And I apt install `openssh-client openssh-server strongswan`
    And I run `pro enable fips` `with sudo` and stdin `y\ny`
    Then if `<release>` in `focal` and stdout contains substring:
      """
      This will install the FIPS packages. The Livepatch service will be unavailable.
      Warning: This action can take some time and cannot be undone.
      Are you sure? (y/N) The "generic" variant of fips is based on the "generic" Ubuntu
      kernel but this machine is running the "kvm" kernel.
      The "kvm" kernel may have significant hardware support
      differences from "generic" fips.

      Warning: Installing generic fips may result in lost hardware support
               and may prevent the system from booting.

      Do you accept the risk and wish to continue? (y/N) Configuring APT access to FIPS
      Updating FIPS package lists
      Updating standard Ubuntu package lists
      Installing FIPS packages
      FIPS enabled
      A reboot is required to complete install.
      """
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
    And I apply this jq filter `.services[] | select(.name == "livepatch") | .available` to the output
    Then I will see the following on stdout:
      """
      "no"
      """
    When I run shell command `pro status --format json --all` with sudo
    And I apply this jq filter `.services[] | select(.name == "livepatch") | .blocked_by[0].reason_code` to the output
    Then I will see the following on stdout:
      """
      "livepatch-invalidates-fips"
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
    And I run `pro enable fips-updates` `with sudo` and stdin `y\ny`
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
    And if `<release>` in `jammy` and stdout contains substring:
      """
      Installing libcharon-extauth-plugins libstrongswan libstrongswan-standard-plugins openssh-client openssh-server openssh-sftp-server openssl-fips-module-3 strongswan strongswan-charon strongswan-libcharon strongswan-starter
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
  Scenario Outline: Attached enable fips on a machine with livepatch active
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then stdout matches regexp:
      """
      Ubuntu Pro: ESM Infra enabled
      """
    And stdout matches regexp:
      """
      Enabling Livepatch
      Livepatch enabled
      """
    When I run `pro enable fips --assume-yes` with sudo
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Disabling incompatible service: Livepatch
      Executing `/snap/bin/canonical-livepatch disable`
      Configuring APT access to FIPS
      Updating FIPS package lists
      Updating standard Ubuntu package lists
      Installing FIPS packages
      FIPS enabled
      A reboot is required to complete install.
      """
    When I run `pro status --all` with sudo
    Then stdout matches regexp:
      """
      fips +yes +enabled
      """
    And stdout matches regexp:
      """
      livepatch +yes +n/a
      """

    Examples: ubuntu release
      | release | machine_type |
      | bionic  | lxd-vm       |
      | xenial  | lxd-vm       |

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

  @slow
  Scenario Outline: Attached enable fips-updates without the -updates pocket enabled
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then I verify that `fips-updates` is disabled
    # Disable the -updates pocket
    When I run `sed -i '/<release>-updates/d' /etc/apt/sources.list` with sudo
    And I apt update
    And I run `pro enable fips-updates --assume-yes` with sudo
    Then I verify that `fips-updates` is enabled

    Examples: ubuntu release
      | release | machine_type |
      | jammy   | lxd-vm       |

  Scenario Outline: Enable fips-updates service access-only
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    When I run `pro enable fips-updates --access-only --assume-yes` with sudo
    Then stdout matches regexp:
      """
      One moment, checking your subscription first
      Configuring APT access to FIPS Updates
      Updating FIPS Updates package lists
      Skipping installing packages: ubuntu-fips
      FIPS Updates access enabled
      """
    Then stdout does not match regexp:
      """
      A reboot is required to complete install.
      """
    When I run `apt-cache policy ubuntu-fips` as non-root
    Then stdout matches regexp:
      """
      .*Installed: \(none\)
      """
    And stdout matches regexp:
      """
      \s* 1001 https://esm.ubuntu.com/fips-updates/ubuntu <release>-updates/main amd64 Packages
      """
    When I run `pro status` as non-root
    Then stdout matches regexp:
      """
      fips-updates +yes +warning
      """
    And stdout contains substring:
      """
      NOTICES
      The following packages are not installed:
      ubuntu-fips
      fips-updates may not be enabled on this system.
      """
    When I run `pro api u.pro.status.enabled_services.v1` with sudo
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "enabled_services": [
            {
              "name": "fips-updates",
              "variant_enabled": false,
              "variant_name": null
            }
          ]
        },
        "meta": {
          "environment_vars": []
        },
        "type": "EnabledServices"
      }
      """
    And API warnings field output is:
      """
      [
        {
          "code": "fips-packages-missing",
          "meta": {
            "service": "fips-updates"
          },
          "title": "The following packages are not installed:\nubuntu-fips\nfips-updates may not be enabled on this system."
        }
      ]
      """
    When I apt install `ubuntu-fips`
    And I reboot the machine
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      fips-updates +yes +enabled
      """
    And stdout does not contain substring:
      """
      fips-updates may not be enabled on this system.
      """
    When I run `uname -r` as non-root
    Then stdout matches regexp:
      """
      fips
      """

    Examples: ubuntu release
      | release | machine_type |
      | jammy   | lxd-vm       |
