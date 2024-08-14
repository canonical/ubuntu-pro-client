@uses.config.contract_token
Feature: Enable usg on Ubuntu

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
