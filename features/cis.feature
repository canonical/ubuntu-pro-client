@uses.config.contract_token
Feature: Enable cis on Ubuntu

  Scenario Outline: Attached enable of cis service in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I verify that running `pro enable cis --access-only` `with sudo` exits `0`
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Configuring APT access to CIS Audit
      Updating CIS Audit package lists
      Skipping installing packages: usg-cisbenchmark usg-common
      CIS Audit access enabled
      Visit https://ubuntu.com/security/cis to learn how to use CIS
      """
    When I run `pro disable cis` with sudo
    And I verify that running `pro enable cis` `with sudo` exits `0`
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Configuring APT access to CIS Audit
      Updating CIS Audit package lists
      Updating standard Ubuntu package lists
      Installing CIS Audit packages
      CIS Audit enabled
      Visit https://ubuntu.com/security/cis to learn how to use CIS
      """
    When I run `apt-cache policy usg-cisbenchmark` as non-root
    Then stdout does not match regexp:
      """
      .*Installed: \(none\)
      """
    And stdout matches regexp:
      """
      \s* 500 https://esm.ubuntu.com/cis/ubuntu <release>/main amd64 Packages
      """
    When I run `apt-cache policy usg-common` as non-root
    Then stdout does not match regexp:
      """
      .*Installed: \(none\)
      """
    And stdout matches regexp:
      """
      \s* 500 https://esm.ubuntu.com/cis/ubuntu <release>/main amd64 Packages
      """
    When I verify that running `pro enable cis` `with sudo` exits `1`
    Then stdout matches regexp:
      """
      One moment, checking your subscription first
      CIS Audit is already enabled - nothing to do.
      See: sudo pro status
      """
    When I run `cis-audit level1_server` with sudo
    Then stdout matches regexp:
      """
      Title.*Ensure no duplicate UIDs exist
      Rule.*xccdf_com.ubuntu.<release>.cis_rule_CIS-.*
      Result.*pass
      """
    And stdout matches regexp:
      """
      Title.*Ensure default user umask is 027 or more restrictive
      Rule.*xccdf_com.ubuntu.<release>.cis_rule_CIS-.*
      Result.*fail
      """
    And stdout matches regexp:
      """
      CIS audit scan completed
      """
    When I verify that running `/usr/share/ubuntu-scap-security-guides/cis-hardening/<cis_script> lvl1_server` `with sudo` exits `0`
    And I run `cis-audit level1_server` with sudo
    Then stdout matches regexp:
      """
      Title.*Ensure default user umask is 027 or more restrictive
      Rule.*xccdf_com.ubuntu.<release>.cis_rule_CIS-.*
      Result.*pass
      """
    And stdout matches regexp:
      """
      CIS audit scan completed
      """

    Examples: cis script
      | release | machine_type  | cis_script                                  |
      | bionic  | lxd-container | Canonical_Ubuntu_18.04_CIS-harden.sh        |
      | xenial  | lxd-container | Canonical_Ubuntu_16.04_CIS_v1.1.0-harden.sh |

  Scenario Outline: Attached enable of cis service in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I verify that running `pro enable cis` `with sudo` exits `0`
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
    When I run `apt-cache policy usg-cisbenchmark` as non-root
    Then stdout does not match regexp:
      """
      .*Installed: \(none\)
      """
    And stdout matches regexp:
      """
      \s* 500 https://esm.ubuntu.com/cis/ubuntu <release>/main amd64 Packages
      """
    When I run `apt-cache policy usg-common` as non-root
    Then stdout does not match regexp:
      """
      .*Installed: \(none\)
      """
    And stdout matches regexp:
      """
      \s* 500 https://esm.ubuntu.com/cis/ubuntu <release>/main amd64 Packages
      """
    When I verify that running `pro enable cis` `with sudo` exits `1`
    Then stdout matches regexp:
      """
      One moment, checking your subscription first
      From Ubuntu 20.04 onward 'pro enable cis' has been
      replaced by 'pro enable usg'. See more information at:
      https://ubuntu.com/security/certifications/docs/usg
      CIS Audit is already enabled - nothing to do.
      See: sudo pro status
      """
    When I run `cis-audit level1_server` with sudo
    Then stdout matches regexp:
      """
      Title.*Ensure no duplicate UIDs exist
      Rule.*xccdf_com.ubuntu.<release>.cis_rule_CIS-.*
      Result.*pass
      """
    And stdout matches regexp:
      """
      Title.*Ensure default user umask is 027 or more restrictive
      Rule.*xccdf_com.ubuntu.<release>.cis_rule_CIS-.*
      Result.*fail
      """
    And stdout matches regexp:
      """
      CIS audit scan completed
      """
    When I verify that running `/usr/share/ubuntu-scap-security-guides/cis-hardening/<cis_script> lvl1_server` `with sudo` exits `0`
    And I run `cis-audit level1_server` with sudo
    Then stdout matches regexp:
      """
      Title.*Ensure default user umask is 027 or more restrictive
      Rule.*xccdf_com.ubuntu.<release>.cis_rule_CIS-.*
      Result.*pass
      """
    And stdout matches regexp:
      """
      CIS audit scan completed
      """

    Examples: cis service
      | release | machine_type  | cis_script                           |
      | focal   | lxd-container | Canonical_Ubuntu_20.04_CIS-harden.sh |
