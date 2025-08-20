@uses.config.contract_token
Feature: ESM legacy service tests

  Scenario Outline: Attached enable of ESM Legacy services in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then I verify that `esm-apps` is enabled
    And I verify that `esm-infra` is enabled
    When I run `pro enable esm-infra-legacy` with sudo
    Then I verify that `esm-infra-legacy` is enabled
    And I verify that `esm-infra` is enabled
    When I run `apt-cache policy` with sudo
    Then apt-cache policy for the following url has priority `510`
      """
      https://esm.ubuntu.com/infra-legacy/ubuntu <release>-infra-legacy-updates/main amd64 Packages
      """
    And apt-cache policy for the following url has priority `510`
      """
      https://esm.ubuntu.com/infra-legacy/ubuntu <release>-infra-legacy-security/main amd64 Packages
      """
    And I ensure apt update runs without errors
    When I apt install `<infra-pkg>`
    And I run `apt-cache policy <infra-pkg>` as non-root
    Then stdout matches regexp:
      """
      \s*510 https://esm.ubuntu.com/infra-legacy/ubuntu <release>-infra-legacy-security/main amd64 Packages
      """
    When I run `pro disable esm-infra` with sudo
    Then I verify that `esm-infra-legacy` is enabled
    And I verify that `esm-infra` is disabled
    When I run `pro disable esm-infra-legacy` with sudo
    Then I verify that `esm-infra-legacy` is disabled
    And I verify that `esm-infra` is disabled
    When I run `pro enable esm-infra-legacy` with sudo
    Then I verify that `esm-infra-legacy` is enabled
    And I verify that `esm-infra` is disabled

    Examples: ubuntu release
      | release | machine_type  | infra-pkg |
      | xenial  | lxd-container | hello     |
