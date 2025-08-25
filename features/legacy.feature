@uses.config.contract_token
Feature: ESM legacy service tests

  Scenario Outline: Attached enable of ESM Legacy services in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token_legacy` with sudo
    Then I verify that `esm-apps` is enabled
    And I verify that `esm-infra` is enabled
    And I verify that `esm-infra-legacy` is enabled
    When I run `pro disable esm-infra-legacy` with sudo
    Then I verify that `esm-infra-legacy` is disabled
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

  Scenario Outline: Attached enable of ESM Apps Legacy services in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token_staging` with sudo
    Then I verify that `esm-apps` is enabled
    And I verify that `esm-infra` is enabled
    When I run `pro enable esm-apps-legacy` with sudo
    Then I verify that `esm-apps-legacy` is enabled
    And I verify that `esm-infra` is enabled
    And I verify that `esm-apps` is enabled
    When I run `apt-cache policy` with sudo
    Then apt-cache policy for the following url has priority `510`
      """
      https://esm.staging.ubuntu.com/apps-legacy/ubuntu <release>-apps-legacy-updates/main amd64 Packages
      """
    And apt-cache policy for the following url has priority `510`
      """
      https://esm.staging.ubuntu.com/apps-legacy/ubuntu <release>-apps-legacy-security/main amd64 Packages
      """
    And I ensure apt update runs without errors
    When I apt install `<apps-pkg>`
    And I run `apt-cache policy <apps-pkg>` as non-root
    Then stdout matches regexp:
      """
      \s*510 https://esm.staging.ubuntu.com/apps-legacy/ubuntu <release>-apps-legacy-security/main amd64 Packages
      """
    When I run `pro disable esm-apps` with sudo
    Then I verify that `esm-apps-legacy` is enabled
    And I verify that `esm-apps` is disabled
    When I run `pro disable esm-apps-legacy` with sudo
    Then I verify that `esm-apps-legacy` is disabled
    And I verify that `esm-apps` is disabled
    When I run `pro enable esm-apps-legacy` with sudo
    Then I verify that `esm-apps-legacy` is enabled
    And I verify that `esm-apps` is disabled

    Examples: ubuntu release
      | release | machine_type  | apps-pkg |
      | xenial  | lxd-container | hello    |

  @uses.config.contract_token @arm64
  Scenario Outline: Attached status with legacy contract in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token_legacy` with sudo
    And I verify root and non-root `pro status` calls have the same output
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +ENTITLED +STATUS   +DESCRIPTION
      cc-eal           +yes      +disabled +Common Criteria EAL2 Provisioning Packages
      cis              +yes      +disabled +Security compliance and audit tools
      esm-apps         +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-apps-legacy  +yes      +enabled  +Expanded Security Maintenance for Applications on Legacy Instances
      esm-infra        +yes      +enabled  +Expanded Security Maintenance for Infrastructure
      esm-infra-legacy +yes      +enabled  +Expanded Security Maintenance for Infrastructure on Legacy Instances
      fips             +yes      +disabled +NIST-certified FIPS crypto packages
      fips-updates     +yes      +disabled +FIPS compliant crypto packages with stable security updates
      ros              +yes      +disabled +Security Updates for the Robot Operating System
      ros-updates      +yes      +disabled +All Updates for the Robot Operating System

      For a list of all Ubuntu Pro services, run 'pro status --all'
      Enable services with: pro enable <service>
      """
    When I verify root and non-root `pro status --all` calls have the same output
    And I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +ENTITLED +STATUS   +DESCRIPTION
      anbox-cloud      +yes      +n/a      +.*
      cc-eal           +yes      +disabled +Common Criteria EAL2 Provisioning Packages
      cis              +yes      +disabled +Security compliance and audit tools
      esm-apps         +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-apps-legacy  +yes      +enabled  +Expanded Security Maintenance for Applications on Legacy Instances
      esm-infra        +yes      +enabled  +Expanded Security Maintenance for Infrastructure
      esm-infra-legacy +yes      +enabled  +Expanded Security Maintenance for Infrastructure on Legacy Instances
      fips             +yes      +disabled +NIST-certified FIPS crypto packages
      fips-preview     +yes      +n/a      +Preview of FIPS crypto packages undergoing certification with NIST
      fips-updates     +yes      +disabled +FIPS compliant crypto packages with stable security updates
      landscape        +yes      +n/a      +Management and administration tool for Ubuntu
      livepatch        +yes      +n/a      +Canonical Livepatch service
      realtime-kernel  +yes      +n/a      +Ubuntu kernel with PREEMPT_RT patches integrated
      ros              +yes      +disabled +Security Updates for the Robot Operating System
      ros-updates      +yes      +disabled +All Updates for the Robot Operating System

      Enable services with: pro enable <service>
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |

  @uses.config.contract_token_legacy
  Scenario Outline: Simulate status in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I do a preflight check for `contract_token_legacy` without the all flag
    Then stdout matches regexp:
      """
      SERVICE          +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
      (anbox-cloud     +yes       +.*)?
      ?cc-eal          +yes       +yes       +no           +Common Criteria EAL2 Provisioning Packages
      cis              +yes       +yes       +no           +Security compliance and audit tools
      esm-apps         +yes       +yes       +yes          +Expanded Security Maintenance for Applications
      esm-apps-legacy  +yes       +yes       +yes          +Expanded Security Maintenance for Applications on Legacy Instances
      esm-infra        +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
      esm-infra-legacy +yes       +yes       +no           +Expanded Security Maintenance for Infrastructure on Legacy Instances
      fips             +yes       +yes       +no           +NIST-certified FIPS crypto packages
      fips-updates     +yes       +yes       +no           +FIPS compliant crypto packages with stable security updates
      livepatch        +yes       +yes       +yes          +Canonical Livepatch service
      ros              +yes       +yes       +no           +Security Updates for the Robot Operating System
      ros-updates      +yes       +yes       +no           +All Updates for the Robot Operating System
      """
    When I do a preflight check for `contract_token_legacy` with the all flag
    Then stdout matches regexp:
      """
      SERVICE          +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
      anbox-cloud      +(yes|no)  +.*
      cc-eal           +yes       +yes       +no           +Common Criteria EAL2 Provisioning Packages
      cis              +yes       +yes       +no           +Security compliance and audit tools
      esm-apps         +yes       +yes       +yes          +Expanded Security Maintenance for Applications
      esm-apps-legacy  +yes       +yes       +yes          +Expanded Security Maintenance for Applications on Legacy Instances
      esm-infra        +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
      esm-infra-legacy +yes       +yes       +no           +Expanded Security Maintenance for Infrastructure on Legacy Instances
      fips             +yes       +yes       +no           +NIST-certified FIPS crypto packages
      fips-preview     +.* +.* +.*
      fips-updates     +yes       +yes       +no           +FIPS compliant crypto packages with stable security updates
      landscape        +no        +yes       +no           +Management and administration tool for Ubuntu
      livepatch        +yes       +yes       +yes          +Canonical Livepatch service
      realtime-kernel  +no        +yes       +no           +Ubuntu kernel with PREEMPT_RT patches integrated
      ros              +yes       +yes       +no           +Security Updates for the Robot Operating System
      ros-updates      +yes       +yes       +no           +All Updates for the Robot Operating System
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
