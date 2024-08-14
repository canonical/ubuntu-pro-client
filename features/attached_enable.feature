@uses.config.contract_token
Feature: Enable command behaviour when attached to an Ubuntu Pro subscription

  Scenario Outline: Attached enable of usg service in a focal machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I run `pro enable usg` with sudo
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Configuring APT access to Ubuntu Security Guide
      Updating Ubuntu Security Guide package lists
      Ubuntu Security Guide enabled
      Visit https://ubuntu.com/security/certifications/docs/usg for the next steps
      """
    And I verify that `usg` is enabled
    When I run `pro disable usg` with sudo
    Then stdout matches regexp:
      """
      Updating package lists
      """
    And I verify that `usg` is disabled
    When I run `pro enable cis` with sudo
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      From Ubuntu 20.04 onward 'pro enable cis' has been
      replaced by 'pro enable usg'. See more information at:
      https://ubuntu.com/security/certifications/docs/usg
      Configuring APT access to CIS Audit
      Updating CIS Audit package lists
      Updating standard Ubuntu package lists
      Installing CIS Audit packages
      CIS Audit enabled
      Visit https://ubuntu.com/security/cis to learn how to use CIS
      """
    And I verify that `usg` is enabled
    When I run `pro disable usg` with sudo
    Then stdout matches regexp:
      """
      Updating package lists
      """
    And I verify that `usg` is disabled

    Examples: cis service
      | release | machine_type  |
      | focal   | lxd-container |
      | focal   | wsl           |

  Scenario Outline: Attached enable livepatch
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then stdout matches regexp:
      """
      Enabling Livepatch
      Livepatch enabled
      """
    And I verify that `livepatch` status is warning
    When I run `pro api u.pro.security.status.reboot_required.v1` with sudo
    Then stdout matches regexp:
      """
      {"_schema_version": "v1", "data": {"attributes": {"livepatch_enabled": true, "livepatch_enabled_and_kernel_patched": true, "livepatch_state": "applied", "livepatch_support": "kernel-upgrade-required", "reboot_required": "no", "reboot_required_packages": {"kernel_packages": null, "standard_packages": null}}, "meta": {"environment_vars": \[\]}, "type": "RebootRequired"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
      """
    When I run `pro system reboot-required` as non-root
    Then I will see the following on stdout:
      """
      no
      """
    When I apt install `libc6`
    And I run `pro api u.pro.security.status.reboot_required.v1` as non-root
    Then stdout matches regexp:
      """
      {"_schema_version": "v1", "data": {"attributes": {"livepatch_enabled": true, "livepatch_enabled_and_kernel_patched": true, "livepatch_state": "applied", "livepatch_support": "kernel-upgrade-required", "reboot_required": "yes", "reboot_required_packages": {"kernel_packages": \[\], "standard_packages": \["libc6"\]}}, "meta": {"environment_vars": \[\]}, "type": "RebootRequired"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
      """
    When I run `pro system reboot-required` as non-root
    Then I will see the following on stdout:
      """
      yes
      """
    When I reboot the machine
    And I run `pro system reboot-required` as non-root
    Then I will see the following on stdout:
      """
      no
      """
    When I apt install `linux-image-generic`
    And I run `pro api u.pro.security.status.reboot_required.v1` as non-root
    Then stdout matches regexp:
      """
      {"_schema_version": "v1", "data": {"attributes": {"livepatch_enabled": true, "livepatch_enabled_and_kernel_patched": true, "livepatch_state": "applied", "livepatch_support": "kernel-upgrade-required", "reboot_required": "yes", "reboot_required_packages": {"kernel_packages": \["linux-base"\], "standard_packages": \[\]}}, "meta": {"environment_vars": \[\]}, "type": "RebootRequired"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
      """
    When I run `pro system reboot-required` as non-root
    Then I will see the following on stdout:
      """
      yes
      """
    When I apt install `dbus`
    And I run `pro api u.pro.security.status.reboot_required.v1` with sudo
    Then stdout matches regexp:
      """
      {"_schema_version": "v1", "data": {"attributes": {"livepatch_enabled": true, "livepatch_enabled_and_kernel_patched": true, "livepatch_state": "applied", "livepatch_support": "kernel-upgrade-required", "reboot_required": "yes", "reboot_required_packages": {"kernel_packages": \["linux-base"\], "standard_packages": \["dbus"\]}}, "meta": {"environment_vars": \[\]}, "type": "RebootRequired"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
      """
    When I run `pro system reboot-required` as non-root
    Then I will see the following on stdout:
      """
      yes
      """

    Examples: ubuntu release
      | release | machine_type |
      | xenial  | lxd-vm       |

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
    Then I will see the following on stdout
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
  Scenario Outline: Attached enable fips on a machine with fips-updates active
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
    When I run `pro disable livepatch` with sudo
    And I run `pro enable fips-updates --assume-yes` with sudo
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Configuring APT access to FIPS Updates
      Updating FIPS Updates package lists
      Updating standard Ubuntu package lists
      Installing FIPS Updates packages
      FIPS Updates enabled
      A reboot is required to complete install.
      """
    When I verify that running `pro enable fips --assume-yes` `with sudo` exits `1`
    Then I will see the following on stdout
      """
      One moment, checking your subscription first
      Cannot enable FIPS when FIPS Updates is enabled.
      Could not enable FIPS.
      """

    Examples: ubuntu release
      | release | machine_type |
      | bionic  | lxd-vm       |
      | xenial  | lxd-vm       |

  # Overall test for overrides; in the future, when many services
  # have overrides, we can consider removing this
  # esm-infra is a good choice because it doesn't already have
  # other overrides that would interfere with the test
  Scenario: Cloud overrides for a generic aws Focal instance
    Given a `focal` `aws.generic` machine with ubuntu-advantage-tools installed
    When I set the machine token overlay to the following yaml
      """
      machineTokenInfo:
        contractInfo:
          resourceEntitlements:
            - type: esm-infra
              overrides:
                - selector:
                    series: focal
                  directives:
                    additionalPackages:
                      - some-package-focal
                - selector:
                    cloud: aws
                  directives:
                    additionalPackages:
                      - some-package-aws
      """
    And I attach `contract_token` with sudo and options `--no-auto-enable`
    And I verify that running `pro enable esm-infra` `with sudo` exits `1`
    Then stdout matches regexp:
      """
      E: Unable to locate package some-package-aws
      """
