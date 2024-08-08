@uses.config.contract_token
Feature: FIPS enablement in lxd VMs

  @slow
  Scenario Outline: Attached enable of FIPS in an ubuntu lxd vm
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    When I run `pro status --format json` with sudo
    Then stdout contains substring
      """
      {"available": "yes", "blocked_by": [{"name": "livepatch", "reason": "Livepatch cannot be enabled while running the official FIPS certified kernel. If you would like a FIPS compliant kernel with additional bug fixes and security updates, you can use the FIPS Updates service with Livepatch.", "reason_code": "livepatch-invalidates-fips"}], "description": "NIST-certified FIPS crypto packages", "description_override": null, "entitled": "yes", "name": "fips", "status": "disabled", "status_details": "FIPS is not configured", "warning": null}
      """
    When I run `pro disable livepatch` with sudo
    And I apt install `openssh-client openssh-server strongswan`
    And I run `apt-mark hold openssh-client openssh-server strongswan` with sudo
    And I run `pro enable <fips-service>` `with sudo` and stdin `y`
    Then stdout matches regexp:
      """
      This will install the FIPS packages. The Livepatch service will be unavailable.
      Warning: This action can take some time and cannot be undone.
      """
    And stdout contains substring:
      """
      Updating <fips-name> package lists
      Updating standard Ubuntu package lists
      Installing <fips-name> packages
      <fips-name> enabled
      A reboot is required to complete install.
      """
    When I run `pro status --all` with sudo
    Then stdout matches regexp:
      """
      FIPS support requires system reboot to complete configuration
      """
    And I ensure apt update runs without errors
    And I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
    And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
    And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
    And I verify that `openssh-server-hmac` is installed from apt source `<fips-apt-source>`
    And I verify that `openssh-client-hmac` is installed from apt source `<fips-apt-source>`
    And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`
    When I run `pro status --format json --all` with sudo
    Then stdout contains substring:
      """
      {"available": "no", "blocked_by": [{"name": "fips", "reason": "Livepatch cannot be enabled while running the official FIPS certified kernel. If you would like a FIPS compliant kernel with additional bug fixes and security updates, you can use the FIPS Updates service with Livepatch.", "reason_code": "livepatch-invalidates-fips"}], "description": "Canonical Livepatch service", "description_override": null, "entitled": "yes", "name": "livepatch", "status": "n/a", "status_details": "Cannot enable Livepatch when FIPS is enabled.", "warning": null}
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
    When I run `pro disable <fips-service>` `with sudo` and stdin `y`
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
    Then I verify that `openssh-server` installed version matches regexp `fips`
    And I verify that `openssh-client` installed version matches regexp `fips`
    And I verify that `strongswan` installed version matches regexp `fips`
    And I verify that `openssh-server-hmac` installed version matches regexp `fips`
    And I verify that `openssh-client-hmac` installed version matches regexp `fips`
    And I verify that `strongswan-hmac` installed version matches regexp `fips`
    When I run `apt-mark unhold openssh-client openssh-server strongswan` with sudo
    Then I will see the following on stdout:
      """
      openssh-client was already not hold.
      openssh-server was already not hold.
      strongswan was already not hold.
      """
    And I verify that `<fips-service>` is disabled
    When I run `pro status --all` with sudo
    Then stdout does not match regexp:
      """
      Disabling FIPS requires system reboot to complete operation
      """
    When I run `pro enable <fips-service> --assume-yes --format json --assume-yes` with sudo
    Then stdout is a json matching the `ua_operation` schema
    And I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [], "failed_services": [], "needs_reboot": true, "processed_services": ["<fips-service>"], "result": "success", "warnings": []}
      """
    When I reboot the machine
    And I run `pro disable <fips-service> --assume-yes --format json` with sudo
    Then stdout is a json matching the `ua_operation` schema
    And I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [], "failed_services": [], "needs_reboot": true, "processed_services": ["<fips-service>"], "result": "success", "warnings": []}
      """
    And I verify that `<fips-service>` is disabled

    Examples: ubuntu release
      | release | machine_type | fips-name | fips-service | fips-apt-source                                |
      | xenial  | lxd-vm       | FIPS      | fips         | https://esm.ubuntu.com/fips/ubuntu xenial/main |
      | bionic  | lxd-vm       | FIPS      | fips         | https://esm.ubuntu.com/fips/ubuntu bionic/main |

  @slow
  Scenario Outline: Attached enable of FIPS-updates in an ubuntu lxd vm
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I run `pro disable livepatch` with sudo
    And I apt install `openssh-client openssh-server strongswan`
    When I run `pro enable <fips-service>` `with sudo` and stdin `y`
    Then stdout matches regexp:
      """
      This will install the FIPS packages including security updates.
      Warning: This action can take some time and cannot be undone.
      """
    And stdout contains substring:
      """
      Updating <fips-name> package lists
      Updating standard Ubuntu package lists
      Installing <fips-name> packages
      <fips-name> enabled
      A reboot is required to complete install.
      """
    And I verify that `<fips-service>` is enabled
    And I ensure apt update runs without errors
    And I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
    And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
    And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
    And I verify that `openssh-server-hmac` is installed from apt source `<fips-apt-source>`
    And I verify that `openssh-client-hmac` is installed from apt source `<fips-apt-source>`
    And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`
    When I run `pro status --all --format json` with sudo
    Then stdout contains substring:
      """
      {"available": "no", "blocked_by": [{"name": "fips-updates", "reason": "FIPS cannot be enabled if FIPS Updates has ever been enabled because FIPS Updates installs security patches that aren't officially certified.", "reason_code": "fips-updates-invalidates-fips"}], "description": "NIST-certified FIPS crypto packages", "description_override": null, "entitled": "yes", "name": "fips", "status": "n/a", "status_details": "Cannot enable FIPS when FIPS Updates is enabled.", "warning": null}
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
    When I run `pro disable <fips-service>` `with sudo` and stdin `y`
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
    Then I verify that `openssh-server` installed version matches regexp `fips`
    And I verify that `openssh-client` installed version matches regexp `fips`
    And I verify that `strongswan` installed version matches regexp `fips`
    And I verify that `openssh-server-hmac` installed version matches regexp `fips`
    And I verify that `openssh-client-hmac` installed version matches regexp `fips`
    And I verify that `strongswan-hmac` installed version matches regexp `fips`
    When I run `apt-mark unhold openssh-client openssh-server strongswan` with sudo
    Then I will see the following on stdout:
      """
      openssh-client was already not hold.
      openssh-server was already not hold.
      strongswan was already not hold.
      """
    And I verify that `<fips-service>` is disabled
    When I verify that running `pro enable fips --assume-yes` `with sudo` exits `1`
    Then stdout matches regexp:
      """
      Cannot enable FIPS because FIPS Updates was once enabled.
      """
    And I verify that files exist matching `/var/lib/ubuntu-advantage/services-once-enabled`
    When I run `pro enable <fips-service> --assume-yes` with sudo
    And I reboot the machine
    Then I verify that `<fips-service>` is enabled
    And I verify that `livepatch` is disabled
    When I run `pro enable livepatch --assume-yes` with sudo
    Then I verify that `<fips-service>` is enabled
    And I verify that `livepatch` is enabled
    When I run `pro status --all --format json` with sudo
    Then stdout contains substring:
      """
      {"available": "no", "blocked_by": [{"name": "livepatch", "reason": "Livepatch cannot be enabled while running the official FIPS certified kernel. If you would like a FIPS compliant kernel with additional bug fixes and security updates, you can use the FIPS Updates service with Livepatch.", "reason_code": "livepatch-invalidates-fips"}, {"name": "fips-updates", "reason": "FIPS cannot be enabled if FIPS Updates has ever been enabled because FIPS Updates installs security patches that aren't officially certified.", "reason_code": "fips-updates-invalidates-fips"}], "description": "NIST-certified FIPS crypto packages", "description_override": null, "entitled": "yes", "name": "fips", "status": "n/a", "status_details": "Cannot enable FIPS when FIPS Updates is enabled.", "warning": null}
      """
    When I run `pro disable <fips-service> --assume-yes` with sudo
    And I run `pro enable <fips-service> --assume-yes --format json --assume-yes` with sudo
    Then stdout is a json matching the `ua_operation` schema
    And I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [], "failed_services": [], "needs_reboot": true, "processed_services": ["<fips-service>"], "result": "success", "warnings": []}
      """
    When I reboot the machine
    And I run `pro disable <fips-service> --assume-yes --format json` with sudo
    Then stdout is a json matching the `ua_operation` schema
    And I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [], "failed_services": [], "needs_reboot": true, "processed_services": ["<fips-service>"], "result": "success", "warnings": []}
      """
    And I verify that `<fips-service>` is disabled

    Examples: ubuntu release
      | release | machine_type | fips-name    | fips-service | fips-apt-source                                                |
      | xenial  | lxd-vm       | FIPS Updates | fips-updates | https://esm.ubuntu.com/fips-updates/ubuntu xenial-updates/main |
      | bionic  | lxd-vm       | FIPS Updates | fips-updates | https://esm.ubuntu.com/fips-updates/ubuntu bionic-updates/main |

  @slow
  Scenario Outline: Attached enable FIPS-updates while livepatch is enabled
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then I verify that `fips-updates` is disabled
    And I verify that `livepatch` is enabled
    When I run `pro enable fips-updates --assume-yes` with sudo
    Then stdout contains substring:
      """
      Configuring APT access to FIPS Updates
      Updating FIPS Updates package lists
      Updating standard Ubuntu package lists
      Installing FIPS Updates packages
      FIPS Updates enabled
      A reboot is required to complete install.
      """
    And I verify that `fips-updates` is enabled
    And I verify that `livepatch` is enabled
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

    Examples: ubuntu release
      | release | machine_type |
      | xenial  | lxd-vm       |
      | bionic  | lxd-vm       |

  @slow
  Scenario Outline: Attached enable of FIPS in an ubuntu lxd vm
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    And I apt install `openssh-client openssh-server strongswan`
    When I run `pro enable <fips-service>` `with sudo` and stdin `y\ny`
    Then stdout contains substring:
      """
      This will install the FIPS packages. The Livepatch service will be unavailable.
      Warning: This action can take some time and cannot be undone.
      Are you sure? (y/N) The "generic" variant of fips is based on the "generic" Ubuntu
      kernel but this machine is running the "kvm" kernel.
      The "kvm" kernel may have significant hardware support
      differences from "generic" fips.

      Warning: Installing generic fips may result in lost hardware support
               and may prevent the system from booting.

      Do you accept the risk and wish to continue? (y/N) Configuring APT access to <fips-name>
      Updating <fips-name> package lists
      Updating standard Ubuntu package lists
      Installing <fips-name> packages
      <fips-name> enabled
      A reboot is required to complete install.
      """
    And I verify that `<fips-service>` is enabled
    And I ensure apt update runs without errors
    And I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
    And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
    And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
    And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`
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
    When I run `pro disable <fips-service> --assume-yes` with sudo
    Then stdout matches regexp:
      """
      Updating package lists
      A reboot is required to complete disable operation
      """
    When I reboot the machine
    Then I verify that `openssh-server` installed version matches regexp `fips`
    And I verify that `openssh-client` installed version matches regexp `fips`
    And I verify that `strongswan` installed version matches regexp `fips`
    And I verify that `strongswan-hmac` installed version matches regexp `fips`
    When I run `apt-mark unhold openssh-client openssh-server strongswan` with sudo
    Then I will see the following on stdout:
      """
      openssh-client was already not hold.
      openssh-server was already not hold.
      strongswan was already not hold.
      """
    And I verify that `<fips-service>` is disabled

    Examples: ubuntu release
      | release | machine_type | fips-name | fips-service | fips-apt-source                               |
      | focal   | lxd-vm       | FIPS      | fips         | https://esm.ubuntu.com/fips/ubuntu focal/main |

  @slow
  Scenario Outline: Attached enable of FIPS-updates in an ubuntu lxd vm
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I apt install `openssh-client openssh-server strongswan`
    When I run `pro enable <fips-service> --assume-yes` with sudo
    Then stdout contains substring:
      """
      Updating <fips-name> package lists
      Updating standard Ubuntu package lists
      Installing <fips-name> packages
      <fips-name> enabled
      A reboot is required to complete install.
      """
    And I verify that `<fips-service>` is enabled
    And I ensure apt update runs without errors
    And I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
    And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
    And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
    And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`
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
    When I run `pro disable <fips-service> --assume-yes` with sudo
    Then stdout matches regexp:
      """
      Updating package lists
      A reboot is required to complete disable operation
      """
    When I reboot the machine
    Then I verify that `openssh-server` installed version matches regexp `<fips-package-str>`
    And I verify that `openssh-client` installed version matches regexp `<fips-package-str>`
    And I verify that `strongswan` installed version matches regexp `<fips-package-str>`
    And I verify that `strongswan-hmac` installed version matches regexp `<fips-package-str>`
    When I run `apt-mark unhold openssh-client openssh-server strongswan` with sudo
    Then stdout matches regexp:
      """
      openssh-client was already (not|not on) hold.
      openssh-server was already (not|not on) hold.
      strongswan was already (not|not on) hold.
      """
    And I verify that `<fips-service>` is disabled
    When I verify that running `pro enable fips --assume-yes` `with sudo` exits `1`
    Then stdout matches regexp:
      """
      Cannot enable FIPS because FIPS Updates was once enabled.
      """
    And I verify that files exist matching `/var/lib/ubuntu-advantage/services-once-enabled`

    Examples: ubuntu release
      | release | machine_type | fips-name    | fips-service | fips-package-str | fips-apt-source                                               | installing-line |
      | focal   | lxd-vm       | FIPS Updates | fips-updates | fips             | https://esm.ubuntu.com/fips-updates/ubuntu focal-updates/main |                 |

  @slow
  Scenario Outline: Attached enable of FIPS-updates in an ubuntu lxd vm with auto-upgrade
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I apt install `openssh-client openssh-server strongswan`
    When I run `pro enable <fips-service> --assume-yes` with sudo
    Then stdout contains substring:
      """
      Updating <fips-name> package lists
      Updating standard Ubuntu package lists
      Installing <fips-name> packages
      Installing libcharon-extauth-plugins libstrongswan libstrongswan-standard-plugins openssh-client openssh-server openssh-sftp-server strongswan strongswan-charon strongswan-libcharon strongswan-starter
      <fips-name> enabled
      A reboot is required to complete install.
      """
    And I verify that `<fips-service>` is enabled
    And I ensure apt update runs without errors
    And I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
    And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
    And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
    And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`
    When I reboot the machine
    And I run `uname -r` as non-root
    Then stdout contains substring:
      """
      fips
      """
    When I run `cat /proc/sys/crypto/fips_enabled` with sudo
    Then I will see the following on stdout:
      """
      1
      """
    When I run `apt-mark unhold openssh-client openssh-server strongswan` with sudo
    Then stdout contains substring:
      """
      openssh-client was already not on hold.
      openssh-server was already not on hold.
      strongswan was already not on hold.
      """

    Examples: ubuntu release
      | release | machine_type | fips-name    | fips-service | fips-apt-source                                               |
      | jammy   | lxd-vm       | FIPS Updates | fips-updates | https://esm.ubuntu.com/fips-updates/ubuntu jammy-updates/main |

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
