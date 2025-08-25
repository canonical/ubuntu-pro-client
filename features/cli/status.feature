Feature: CLI status command

  @uses.config.contract_token
  Scenario Outline: Attached status in a ubuntu machine with feature overrides
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/var/lib/ubuntu-advantage/machine-token-overlay.json` with the following:
      """
      {
          "machineTokenInfo": {
              "contractInfo": {
                  "resourceEntitlements": [
                      {
                          "type": "cc-eal",
                          "entitled": false
                      }
                  ]
              }
          }
      }
      """
    And I append the following on uaclient config:
      """
      features:
        machine_token_overlay: "/var/lib/ubuntu-advantage/machine-token-overlay.json"
        other: false
      """
    And I attach `contract_token` with sudo
    And I run `pro status --all` with sudo
    Then stdout matches regexp:
      """
      SERVICE       +ENTITLED +STATUS +DESCRIPTION
      anbox-cloud   +.*
      cc-eal        +no
      """
    And stdout matches regexp:
      """
      FEATURES
      machine_token_overlay: /var/lib/ubuntu-advantage/machine-token-overlay.json
      other: False
      """
    When I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      SERVICE       +ENTITLED +STATUS +DESCRIPTION
      anbox-cloud   +.*
      cc-eal        +no
      """
    And stdout matches regexp:
      """
      FEATURES
      machine_token_overlay: /var/lib/ubuntu-advantage/machine-token-overlay.json
      other: False
      """
    When I create the file `/var/lib/ubuntu-advantage/machine-token-overlay.json` with the following:
      """
      {
          "machineTokenInfo": {
              "contractInfo": {
                  "effectiveTo": null
              }
          }
      }
      """
    And I run `pro status` with sudo
    Then stdout contains substring:
      """
      Valid until: Unknown/Expired
      """
    And I verify that `/var/lib/ubuntu-advantage/status.json` is owned by `root:root` with permission `644`

    Examples: ubuntu release
      | release  | machine_type  |
      | bionic   | lxd-container |
      | focal    | lxd-container |
      | xenial   | lxd-container |
      | jammy    | lxd-container |
      | noble    | lxd-container |
      | oracular | lxd-container |
      | plucky   | lxd-container |

  @uses.config.contract_token @arm64
  Scenario Outline: Non-root status can see in-progress operations
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    When I run shell command `sudo pro refresh & pro status` as non-root
    Then stdout matches regexp:
      """
      NOTICES
      Operation in progress: pro refresh
      """
    When I run `pro status --wait` as non-root
    When I run shell command `sudo pro refresh & pro status --wait` as non-root
    Then stdout matches regexp:
      """
      Successfully processed your pro configuration.
      Successfully refreshed your subscription.
      Successfully updated Ubuntu Pro related APT and MOTD messages.
      \.+
      SERVICE +ENTITLED +STATUS +DESCRIPTION
      """
    Then stdout does not match regexp:
      """
      NOTICES
      Operation in progress: pro refresh
      """
    When I apt install `jq`
    When I run shell command `sudo pro refresh >/dev/null & pro status --format json | jq -r .execution_status` as non-root
    Then I will see the following on stdout:
      """
      active
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |

  Scenario Outline: Attached status in a Xenial GCP Pro machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
      """
      contract_url: 'https://contracts.canonical.com'
      log_level: debug
      """
    And I run `pro auto-attach` with sudo
    And I verify root and non-root `pro status` calls have the same output
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +ENTITLED +STATUS   +DESCRIPTION
      cc-eal           +yes      +disabled +Common Criteria EAL2 Provisioning Packages
      cis              +yes      +disabled +Security compliance and audit tools
      esm-apps         +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra        +yes      +enabled  +Expanded Security Maintenance for Infrastructure
      livepatch        +yes      +warning  +Current kernel is not covered by livepatch
      """
    When I verify root and non-root `pro status --all` calls have the same output
    And I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +ENTITLED +STATUS   +DESCRIPTION
      anbox-cloud      +yes      +n/a      +Scalable Android in the cloud
      cc-eal           +yes      +disabled +Common Criteria EAL2 Provisioning Packages
      cis              +yes      +disabled +Security compliance and audit tools
      esm-apps         +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra        +yes      +enabled  +Expanded Security Maintenance for Infrastructure
      fips             +yes      +n/a      +NIST-certified FIPS crypto packages
      fips-preview     +yes      +n/a      +Preview of FIPS crypto packages undergoing certification with NIST
      fips-updates     +yes      +n/a      +FIPS compliant crypto packages with stable security updates
      landscape        +yes      +n/a      +Management and administration tool for Ubuntu
      livepatch        +yes      +warning  +Current kernel is not covered by livepatch
      """

    Examples: ubuntu release
      | release | machine_type |
      | xenial  | gcp.pro      |

  Scenario Outline: Attached status in a ubuntu Pro machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
      """
      contract_url: 'https://contracts.canonical.com'
      log_level: debug
      """
    And I run `pro auto-attach` with sudo
    When I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE         +ENTITLED +STATUS   +DESCRIPTION
      cc-eal          +yes      +disabled +Common Criteria EAL2 Provisioning Packages
      cis             +yes      +disabled +Security compliance and audit tools
      esm-apps        +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra       +yes      +enabled  +Expanded Security Maintenance for Infrastructure
      fips            +yes      +disabled +NIST-certified FIPS crypto packages
      fips-updates    +yes      +disabled +FIPS compliant crypto packages with stable security updates
      livepatch       +yes      +enabled  +Canonical Livepatch service
      """
    When I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +ENTITLED +STATUS   +DESCRIPTION
      anbox-cloud      +yes      +n/a      +Scalable Android in the cloud
      cc-eal           +yes      +disabled +Common Criteria EAL2 Provisioning Packages
      cis              +yes      +disabled +Security compliance and audit tools
      esm-apps         +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra        +yes      +enabled  +Expanded Security Maintenance for Infrastructure
      fips             +yes      +disabled +NIST-certified FIPS crypto packages
      fips-preview     +yes      +n/a      +Preview of FIPS crypto packages undergoing certification with NIST
      fips-updates     +yes      +disabled +FIPS compliant crypto packages with stable security updates
      landscape        +yes      +n/a      +Management and administration tool for Ubuntu
      livepatch        +yes      +enabled  +Canonical Livepatch service
      """

    Examples: ubuntu release
      | release | machine_type |
      | xenial  | aws.pro      |
      | xenial  | azure.pro    |
      | bionic  | aws.pro      |
      | bionic  | azure.pro    |
      | bionic  | gcp.pro      |

  Scenario Outline: Attached status in a Focal Pro machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
      """
      contract_url: 'https://contracts.canonical.com'
      log_level: debug
      """
    And I run `pro auto-attach` with sudo
    And I verify root and non-root `pro status` calls have the same output
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE         +ENTITLED +STATUS   +DESCRIPTION
      anbox-cloud     +yes      +disabled +Scalable Android in the cloud
      esm-apps        +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra       +yes      +enabled  +Expanded Security Maintenance for Infrastructure
      fips            +yes      +disabled +NIST-certified FIPS crypto packages
      fips-updates    +yes      +disabled +FIPS compliant crypto packages with stable security updates
      livepatch       +yes      +enabled  +Canonical Livepatch service
      usg             +yes      +disabled +Security compliance and audit tools
      """
    When I verify root and non-root `pro status --all` calls have the same output
    And I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +ENTITLED +STATUS   +DESCRIPTION
      anbox-cloud      +yes      +disabled +Scalable Android in the cloud
      cc-eal           +yes      +n/a      +Common Criteria EAL2 Provisioning Packages
      esm-apps         +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra        +yes      +enabled  +Expanded Security Maintenance for Infrastructure
      esm-infra-legacy +yes      +n/a      +Expanded Security Maintenance for Infrastructure on Legacy Instances
      fips             +yes      +disabled +NIST-certified FIPS crypto packages
      fips-preview     +yes      +n/a      +Preview of FIPS crypto packages undergoing certification with NIST
      fips-updates     +yes      +disabled +FIPS compliant crypto packages with stable security updates
      landscape        +yes      +n/a      +Management and administration tool for Ubuntu
      livepatch        +yes      +enabled  +Canonical Livepatch service
      usg              +yes      +disabled +Security compliance and audit tools
      """

    Examples: ubuntu release
      | release | machine_type |
      | focal   | azure.pro    |
      | focal   | gcp.pro      |

  Scenario Outline: Attached status in a Focal AWS Pro machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
      """
      contract_url: 'https://contracts.canonical.com'
      log_level: debug
      """
    And I run `pro auto-attach` with sudo
    And I verify root and non-root `pro status` calls have the same output
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +ENTITLED +STATUS   +DESCRIPTION
      anbox-cloud      +yes      +disabled +Scalable Android in the cloud
      esm-apps         +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra        +yes      +enabled  +Expanded Security Maintenance for Infrastructure
      fips             +yes      +disabled +NIST-certified FIPS crypto packages
      fips-updates     +yes      +disabled +FIPS compliant crypto packages with stable security updates
      livepatch        +yes      +enabled  +Canonical Livepatch service
      usg              +yes      +disabled +Security compliance and audit tools
      """
    When I verify root and non-root `pro status --all` calls have the same output
    And I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +ENTITLED +STATUS   +DESCRIPTION
      anbox-cloud      +yes      +disabled +Scalable Android in the cloud
      cc-eal           +yes      +n/a      +Common Criteria EAL2 Provisioning Packages
      esm-apps         +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra        +yes      +enabled  +Expanded Security Maintenance for Infrastructure
      fips             +yes      +disabled +NIST-certified FIPS crypto packages
      fips-preview     +yes      +n/a      +Preview of FIPS crypto packages undergoing certification with NIST
      fips-updates     +yes      +disabled +FIPS compliant crypto packages with stable security updates
      landscape        +yes      +n/a      +Management and administration tool for Ubuntu
      livepatch        +yes      +enabled  +Canonical Livepatch service
      realtime-kernel  +yes      +n/a      +Ubuntu kernel with PREEMPT_RT patches integrated
      usg              +yes      +disabled +Security compliance and audit tools
      """

    Examples: ubuntu release
      | release | machine_type |
      | focal   | aws.pro      |

  Scenario Outline: Attached status in Jammy Pro machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
      """
      contract_url: 'https://contracts.canonical.com'
      log_level: debug
      """
    And I run `pro auto-attach` with sudo
    And I verify root and non-root `pro status` calls have the same output
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE         +ENTITLED +STATUS   +DESCRIPTION
      anbox-cloud     +yes      +disabled +Scalable Android in the cloud
      esm-apps        +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra       +yes      +enabled  +Expanded Security Maintenance for Infrastructure
      fips-preview    +yes      +disabled +Preview of FIPS crypto packages undergoing certification with NIST
      fips-updates    +yes      +disabled +FIPS compliant crypto packages with stable security updates
      livepatch       +yes      +enabled  +Canonical Livepatch service
      usg             +yes      +disabled +Security compliance and audit tools
      """
    When I verify root and non-root `pro status --all` calls have the same output
    And I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +ENTITLED +STATUS   +DESCRIPTION
      anbox-cloud      +yes      +disabled +Scalable Android in the cloud
      cc-eal           +yes      +n/a      +Common Criteria EAL2 Provisioning Packages
      esm-apps         +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra        +yes      +enabled  +Expanded Security Maintenance for Infrastructure
      fips             +yes      +n/a      +NIST-certified FIPS crypto packages
      fips-preview     +yes      +disabled +Preview of FIPS crypto packages undergoing certification with NIST
      fips-updates     +yes      +disabled +FIPS compliant crypto packages with stable security updates
      landscape        +yes      +n/a      +Management and administration tool for Ubuntu
      livepatch        +yes      +enabled  +Canonical Livepatch service
      usg              +yes      +disabled +Security compliance and audit tools
      """

    Examples: ubuntu release
      | release | machine_type |
      | jammy   | azure.pro    |
      | jammy   | gcp.pro      |

  Scenario Outline: Attached status in Jammy AWS Pro machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
      """
      contract_url: 'https://contracts.canonical.com'
      log_level: debug
      """
    And I run `pro auto-attach` with sudo
    And I verify root and non-root `pro status` calls have the same output
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE +ENTITLED +STATUS +DESCRIPTION
      anbox-cloud      +yes      +disabled +Scalable Android in the cloud
      esm-apps         +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra        +yes      +enabled  +Expanded Security Maintenance for Infrastructure
      fips-preview     +yes      +disabled +Preview of FIPS crypto packages undergoing certification with NIST
      fips-updates     +yes      +disabled +FIPS compliant crypto packages with stable security updates
      livepatch        +yes      +enabled  +Canonical Livepatch service
      realtime-kernel\* +yes      +disabled +Ubuntu kernel with PREEMPT_RT patches integrated
      usg              +yes      +disabled +Security compliance and audit tools
      """
    When I verify root and non-root `pro status --all` calls have the same output
    And I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +ENTITLED +STATUS   +DESCRIPTION
      anbox-cloud      +yes      +disabled +Scalable Android in the cloud
      cc-eal           +yes      +n/a      +Common Criteria EAL2 Provisioning Packages
      esm-apps         +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra        +yes      +enabled  +Expanded Security Maintenance for Infrastructure
      fips             +yes      +n/a      +NIST-certified FIPS crypto packages
      fips-preview     +yes      +disabled +Preview of FIPS crypto packages undergoing certification with NIST
      fips-updates     +yes      +disabled +FIPS compliant crypto packages with stable security updates
      landscape        +yes      +n/a      +Management and administration tool for Ubuntu
      livepatch        +yes      +enabled  +Canonical Livepatch service
      realtime-kernel  +yes      +disabled +Ubuntu kernel with PREEMPT_RT patches integrated
      ├ generic        *yes      +disabled +Generic version of the RT kernel \(default\)
      ├ intel-iotg     *yes      +disabled +RT kernel optimized for Intel IOTG platform
      └ raspi          *yes      +n/a      +24.04 Real-time kernel optimised for Raspberry Pi
      usg              +yes      +disabled +Security compliance and audit tools
      """

    Examples: ubuntu release
      | release | machine_type |
      | jammy   | aws.pro      |

  @uses.config.contract_token @arm64
  Scenario Outline: Attached status in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I verify root and non-root `pro status` calls have the same output
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +ENTITLED +STATUS   +DESCRIPTION
      cc-eal           +yes      +disabled +Common Criteria EAL2 Provisioning Packages
      cis              +yes      +disabled +Security compliance and audit tools
      esm-apps         +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra        +yes      +enabled  +Expanded Security Maintenance for Infrastructure
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
      esm-infra        +yes      +enabled  +Expanded Security Maintenance for Infrastructure
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

  @uses.config.contract_token @arm64
  Scenario Outline: Attached status in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I verify root and non-root `pro status` calls have the same output
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE         +ENTITLED +STATUS   +DESCRIPTION
      esm-apps        +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra       +yes      +enabled  +Expanded Security Maintenance for Infrastructure

      For a list of all Ubuntu Pro services, run 'pro status --all'
      Enable services with: pro enable <service>
      """
    When I verify root and non-root `pro status --all` calls have the same output
    And I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      SERVICE         +ENTITLED +STATUS   +DESCRIPTION
      anbox-cloud     +yes      +n/a      +.*
      cc-eal          +yes      +n/a      +Common Criteria EAL2 Provisioning Packages
      cis             +yes      +n/a      +Security compliance and audit tools
      esm-apps        +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra       +yes      +enabled  +Expanded Security Maintenance for Infrastructure
      fips            +yes      +n/a      +NIST-certified FIPS crypto packages
      fips-preview    +yes      +n/a      +Preview of FIPS crypto packages undergoing certification with NIST
      fips-updates    +yes      +n/a      +FIPS compliant crypto packages with stable security updates
      landscape       +yes      +n/a      +Management and administration tool for Ubuntu
      livepatch       +yes      +n/a      +Canonical Livepatch service
      realtime-kernel +yes      +n/a      +Ubuntu kernel with PREEMPT_RT patches integrated
      ros             +yes      +n/a      +Security Updates for the Robot Operating System
      ros-updates     +yes      +n/a      +All Updates for the Robot Operating System

      Enable services with: pro enable <service>
      """

    Examples: ubuntu release
      | release | machine_type |
      | bionic  | wsl          |

  @uses.config.contract_token @arm64
  Scenario Outline: Attached status in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I verify root and non-root `pro status` calls have the same output
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE         +ENTITLED +STATUS   +DESCRIPTION
      esm-apps        +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra       +yes      +enabled  +Expanded Security Maintenance for Infrastructure

      For a list of all Ubuntu Pro services, run 'pro status --all'
      Enable services with: pro enable <service>
      """
    When I verify root and non-root `pro status --all` calls have the same output
    And I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +ENTITLED +STATUS   +DESCRIPTION
      anbox-cloud      +yes      +n/a      +.*
      cc-eal           +yes      +n/a      +Common Criteria EAL2 Provisioning Packages
      esm-apps         +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra        +yes      +enabled  +Expanded Security Maintenance for Infrastructure
      fips             +yes      +n/a      +NIST-certified FIPS crypto packages
      fips-preview     +yes      +n/a      +Preview of FIPS crypto packages undergoing certification with NIST
      fips-updates     +yes      +n/a      +FIPS compliant crypto packages with stable security updates
      landscape        +yes      +n/a      +Management and administration tool for Ubuntu
      livepatch        +yes      +n/a      +Canonical Livepatch service
      realtime-kernel  +yes      +n/a      +Ubuntu kernel with PREEMPT_RT patches integrated
      ros              +yes      +n/a      +Security Updates for the Robot Operating System
      ros-updates      +yes      +n/a      +All Updates for the Robot Operating System
      usg              +yes      +n/a      +Security compliance and audit tools

      Enable services with: pro enable <service>
      """

    Examples: ubuntu release
      | release | machine_type |
      | focal   | wsl          |

  @uses.config.contract_token
  Scenario Outline: Attached status in a Focal ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I verify root and non-root `pro status` calls have the same output
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE         +ENTITLED +STATUS   +DESCRIPTION
      anbox-cloud     +yes      +disabled +.*
      esm-apps        +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra       +yes      +enabled  +Expanded Security Maintenance for Infrastructure
      fips            +yes      +disabled +NIST-certified FIPS crypto packages
      fips-updates    +yes      +disabled +FIPS compliant crypto packages with stable security updates
      ros             +yes      +disabled +Security Updates for the Robot Operating System
      usg             +yes      +disabled +Security compliance and audit tools

      For a list of all Ubuntu Pro services, run 'pro status --all'
      Enable services with: pro enable <service>
      """
    When I verify root and non-root `pro status --all` calls have the same output
    And I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +ENTITLED +STATUS   +DESCRIPTION
      anbox-cloud      +yes      +disabled +.*
      cc-eal           +yes      +n/a      +Common Criteria EAL2 Provisioning Packages
      esm-apps         +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra        +yes      +enabled  +Expanded Security Maintenance for Infrastructure
      fips             +yes      +disabled +NIST-certified FIPS crypto packages
      fips-preview     +yes      +n/a      +Preview of FIPS crypto packages undergoing certification with NIST
      fips-updates     +yes      +disabled +FIPS compliant crypto packages with stable security updates
      landscape        +yes      +n/a      +Management and administration tool for Ubuntu
      livepatch        +yes      +n/a      +Canonical Livepatch service
      realtime-kernel  +yes      +n/a      +Ubuntu kernel with PREEMPT_RT patches integrated
      ros              +yes      +disabled +Security Updates for the Robot Operating System
      ros-updates      +yes      +n/a      +All Updates for the Robot Operating System
      usg              +yes      +disabled +Security compliance and audit tools

      Enable services with: pro enable <service>
      """

    Examples: ubuntu release
      | release | machine_type  |
      | focal   | lxd-container |

  @uses.config.contract_token
  Scenario Outline: Attached status in a Jammy ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I verify root and non-root `pro status` calls have the same output
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE         +ENTITLED +STATUS   +DESCRIPTION
      anbox-cloud     +yes      +disabled +.*
      esm-apps        +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra       +yes      +enabled  +Expanded Security Maintenance for Infrastructure
      fips-preview    +yes      +disabled +Preview of FIPS crypto packages undergoing certification with NIST
      fips-updates    +yes      +disabled +FIPS compliant crypto packages with stable security updates
      usg             +yes      +disabled +Security compliance and audit tools

      For a list of all Ubuntu Pro services, run 'pro status --all'
      Enable services with: pro enable <service>
      """
    When I verify root and non-root `pro status --all` calls have the same output
    And I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +ENTITLED +STATUS   +DESCRIPTION
      anbox-cloud      +yes      +disabled +.*
      cc-eal           +yes      +n/a      +Common Criteria EAL2 Provisioning Packages
      esm-apps         +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra        +yes      +enabled  +Expanded Security Maintenance for Infrastructure
      fips             +yes      +n/a      +NIST-certified FIPS crypto packages
      fips-preview     +yes      +disabled +Preview of FIPS crypto packages undergoing certification with NIST
      fips-updates     +yes      +disabled +FIPS compliant crypto packages with stable security updates
      landscape        +yes      +n/a      +Management and administration tool for Ubuntu
      livepatch        +yes      +n/a      +Canonical Livepatch service
      realtime-kernel  +yes      +n/a      +Ubuntu kernel with PREEMPT_RT patches integrated
      ├ generic        +yes      +n/a      +Generic version of the RT kernel \(default\)
      ├ intel-iotg     +yes      +n/a      +RT kernel optimized for Intel IOTG platform
      └ raspi          +yes      +n/a      +24.04 Real-time kernel optimised for Raspberry Pi
      ros              +yes      +n/a      +Security Updates for the Robot Operating System
      ros-updates      +yes      +n/a      +All Updates for the Robot Operating System
      usg              +yes      +disabled +Security compliance and audit tools

      Enable services with: pro enable <service>
      """

    Examples: ubuntu release
      | release | machine_type  |
      | jammy   | lxd-container |

  @uses.config.contract_token @arm64
  Scenario Outline: Attached status in the latest LTS ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I verify root and non-root `pro status` calls have the same output
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE         +ENTITLED +STATUS   +DESCRIPTION
      anbox-cloud     +yes      +disabled +.*
      esm-apps        +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra       +yes      +enabled  +Expanded Security Maintenance for Infrastructure
      landscape       +yes      +disabled +Management and administration tool for Ubuntu
      usg             +yes      +disabled +Security compliance and audit tools

      For a list of all Ubuntu Pro services, run 'pro status --all'
      Enable services with: pro enable <service>
      """
    When I verify root and non-root `pro status --all` calls have the same output
    And I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +ENTITLED +STATUS   +DESCRIPTION
      anbox-cloud      +yes      +disabled +.*
      cc-eal           +yes      +n/a      +Common Criteria EAL2 Provisioning Packages
      esm-apps         +yes      +enabled  +Expanded Security Maintenance for Applications
      esm-infra        +yes      +enabled  +Expanded Security Maintenance for Infrastructure
      fips             +yes      +n/a      +NIST-certified FIPS crypto packages
      fips-preview     +yes      +n/a      +Preview of FIPS crypto packages undergoing certification with NIST
      fips-updates     +yes      +n/a      +FIPS compliant crypto packages with stable security updates
      landscape        +yes      +disabled +Management and administration tool for Ubuntu
      livepatch        +yes      +n/a      +Canonical Livepatch service
      realtime-kernel  +yes      +n/a      +Ubuntu kernel with PREEMPT_RT patches integrated
      ├ generic        +yes      +n/a      +Generic version of the RT kernel \(default\)
      ├ intel-iotg     +yes      +n/a      +RT kernel optimized for Intel IOTG platform
      └ raspi          +yes      +n/a      +24.04 Real-time kernel optimised for Raspberry Pi
      ros              +yes      +n/a      +Security Updates for the Robot Operating System
      ros-updates      +yes      +n/a      +All Updates for the Robot Operating System
      usg              +yes      +disabled +Security compliance and audit tools

      Enable services with: pro enable <service>
      """

    Examples: ubuntu release
      | release | machine_type  |
      | noble   | lxd-container |

  @arm64
  Scenario Outline: Unattached status in a ubuntu machine - formatted
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro status --format json` as non-root
    Then stdout is a json matching the `ua_status` schema
    When I run `pro status --format yaml` as non-root
    Then stdout is a yaml matching the `ua_status` schema
    When I run `sed -i 's/contracts.can/invalidurl.notcan/' /etc/ubuntu-advantage/uaclient.conf` with sudo
    And I verify that running `pro status --format json` `as non-root` exits `1`
    Then stdout is a json matching the `ua_status` schema
    And API full output matches regexp:
      """
      {
        "environment_vars": [],
        "errors": [
          {
            "message": "Failed to connect to .*\n[Errno -2] Name or service not known\n",
            "message_code": "connectivity-error",
            "service": null,
            "type": "system"
          }
        ],
        "result": "failure",
        "services": [],
        "warnings": []
      }
      """
    And I verify that running `pro status --format yaml` `as non-root` exits `1`
    Then stdout is a yaml matching the `ua_status` schema
    And stdout matches regexp:
      """
      environment_vars: \[\]
      errors:
      - message: 'Failed to connect to https://invalidurl.notcanonical.com/v1/resources(.*)

          \[Errno -2\] Name or service not known

          '
        message_code: connectivity-error
        service: null
        type: system
      result: failure
      services: \[\]
      warnings: \[\]
      """

    Examples: ubuntu release
      | release  | machine_type  |
      | bionic   | lxd-container |
      | focal    | lxd-container |
      | xenial   | lxd-container |
      | jammy    | lxd-container |
      | noble    | lxd-container |
      | oracular | lxd-container |
      | plucky   | lxd-container |

  @arm64
  Scenario Outline: Unattached status in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I verify root and non-root `pro status` calls have the same output
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +AVAILABLE +DESCRIPTION
      (anbox-cloud     +(yes|no)  +.*)?
      ?cc-eal          +yes       +Common Criteria EAL2 Provisioning Packages
      cis              +yes       +Security compliance and audit tools
      esm-apps         +yes       +Expanded Security Maintenance for Applications
      esm-apps-legacy  +yes       +Expanded Security Maintenance for Applications on Legacy Instances
      esm-infra        +yes       +Expanded Security Maintenance for Infrastructure
      esm-infra-legacy +yes       +Expanded Security Maintenance for Infrastructure on Legacy Instances
      fips             +yes       +NIST-certified FIPS crypto packages
      fips-updates     +yes       +FIPS compliant crypto packages with stable security updates
      livepatch        +yes       +(Canonical Livepatch service|Current kernel is not covered by livepatch)
      ros              +yes       +Security Updates for the Robot Operating System
      ros-updates      +yes       +All Updates for the Robot Operating System

      For a list of all Ubuntu Pro services, run 'pro status --all'

      This machine is not attached to an Ubuntu Pro subscription.
      See https://ubuntu.com/pro
      """
    When I verify root and non-root `pro status --all` calls have the same output
    And I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +AVAILABLE +DESCRIPTION
      anbox-cloud      +(yes|no)  +.*
      cc-eal           +yes       +Common Criteria EAL2 Provisioning Packages
      cis              +yes       +Security compliance and audit tools
      esm-apps         +yes       +Expanded Security Maintenance for Applications
      esm-apps-legacy  +yes       +Expanded Security Maintenance for Applications on Legacy Instances
      esm-infra        +yes       +Expanded Security Maintenance for Infrastructure
      esm-infra-legacy +yes       +Expanded Security Maintenance for Infrastructure on Legacy Instances
      fips             +yes       +NIST-certified FIPS crypto packages
      fips-preview     +no        +.*
      fips-updates     +yes       +FIPS compliant crypto packages with stable security updates
      landscape        +no        +Management and administration tool for Ubuntu
      livepatch        +yes      +(Canonical Livepatch service|Current kernel is not covered by livepatch)
      realtime-kernel  +no        +Ubuntu kernel with PREEMPT_RT patches integrated
      ros              +yes       +Security Updates for the Robot Operating System
      ros-updates      +yes       +All Updates for the Robot Operating System

      This machine is not attached to an Ubuntu Pro subscription.
      See https://ubuntu.com/pro
      """
    When I append the following on uaclient config:
      """
      features:
          allow_beta: true
      """
    And I verify root and non-root `pro status` calls have the same output
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +AVAILABLE +DESCRIPTION
      (anbox-cloud     +(yes|no)  +.*)?
      ?cc-eal          +yes       +Common Criteria EAL2 Provisioning Packages
      cis              +yes       +Security compliance and audit tools
      esm-apps         +yes       +Expanded Security Maintenance for Applications
      esm-apps-legacy  +yes       +Expanded Security Maintenance for Applications on Legacy Instances
      esm-infra        +yes       +Expanded Security Maintenance for Infrastructure
      esm-infra-legacy +yes       +Expanded Security Maintenance for Infrastructure on Legacy Instances
      fips             +yes       +NIST-certified FIPS crypto packages
      fips-updates     +yes       +FIPS compliant crypto packages with stable security updates
      livepatch        +yes      +(Canonical Livepatch service|Current kernel is not covered by livepatch)
      ros              +yes       +Security Updates for the Robot Operating System
      ros-updates      +yes       +All Updates for the Robot Operating System

      FEATURES
      allow_beta: True

      For a list of all Ubuntu Pro services, run 'pro status --all'

      This machine is not attached to an Ubuntu Pro subscription.
      See https://ubuntu.com/pro
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |

  @arm64
  Scenario Outline: Unattached status in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I verify root and non-root `pro status` calls have the same output
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE         +AVAILABLE +DESCRIPTION
      (anbox-cloud    +(yes|no)  +.*)?
      ?cc-eal         +yes       +Common Criteria EAL2 Provisioning Packages
      cis             +yes       +Security compliance and audit tools
      esm-apps        +yes       +Expanded Security Maintenance for Applications
      esm-infra       +yes       +Expanded Security Maintenance for Infrastructure
      fips            +yes       +NIST-certified FIPS crypto packages
      fips-updates    +yes       +FIPS compliant crypto packages with stable security updates
      livepatch       +yes       +(Canonical Livepatch service|Current kernel is not covered by livepatch)
      ros             +yes       +Security Updates for the Robot Operating System
      ros-updates     +yes       +All Updates for the Robot Operating System

      For a list of all Ubuntu Pro services, run 'pro status --all'

      This machine is not attached to an Ubuntu Pro subscription.
      See https://ubuntu.com/pro
      """
    When I verify root and non-root `pro status --all` calls have the same output
    And I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +AVAILABLE +DESCRIPTION
      anbox-cloud      +(yes|no)  +.*
      cc-eal           +yes       +Common Criteria EAL2 Provisioning Packages
      cis              +yes       +Security compliance and audit tools
      esm-apps         +yes       +Expanded Security Maintenance for Applications
      esm-apps-legacy  +no        +Expanded Security Maintenance for Applications on Legacy Instances
      esm-infra        +yes       +Expanded Security Maintenance for Infrastructure
      esm-infra-legacy +no        +Expanded Security Maintenance for Infrastructure on Legacy Instances
      fips             +yes       +NIST-certified FIPS crypto packages
      fips-preview     +no        +.*
      fips-updates     +yes       +FIPS compliant crypto packages with stable security updates
      landscape        +no        +Management and administration tool for Ubuntu
      livepatch        +yes      +(Canonical Livepatch service|Current kernel is not covered by livepatch)
      realtime-kernel  +no        +Ubuntu kernel with PREEMPT_RT patches integrated
      ros              +yes       +Security Updates for the Robot Operating System
      ros-updates      +yes       +All Updates for the Robot Operating System

      This machine is not attached to an Ubuntu Pro subscription.
      See https://ubuntu.com/pro
      """
    When I append the following on uaclient config:
      """
      features:
          allow_beta: true
      """
    And I verify root and non-root `pro status` calls have the same output
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +AVAILABLE +DESCRIPTION
      (anbox-cloud     +(yes|no)  +.*)?
      ?cc-eal          +yes       +Common Criteria EAL2 Provisioning Packages
      cis              +yes       +Security compliance and audit tools
      esm-apps         +yes       +Expanded Security Maintenance for Applications
      esm-infra        +yes       +Expanded Security Maintenance for Infrastructure
      fips             +yes       +NIST-certified FIPS crypto packages
      fips-updates     +yes       +FIPS compliant crypto packages with stable security updates
      livepatch        +yes      +(Canonical Livepatch service|Current kernel is not covered by livepatch)
      ros              +yes       +Security Updates for the Robot Operating System
      ros-updates      +yes       +All Updates for the Robot Operating System

      FEATURES
      allow_beta: True

      For a list of all Ubuntu Pro services, run 'pro status --all'

      This machine is not attached to an Ubuntu Pro subscription.
      See https://ubuntu.com/pro
      """

    Examples: ubuntu release
      | release | machine_type  |
      | bionic  | lxd-container |

  Scenario Outline: Unattached status in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I verify root and non-root `pro status` calls have the same output
    When I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE         +AVAILABLE +DESCRIPTION
      anbox-cloud     +yes       +.*
      esm-apps        +yes       +Expanded Security Maintenance for Applications
      esm-infra       +yes       +Expanded Security Maintenance for Infrastructure
      fips            +yes       +NIST-certified FIPS crypto packages
      fips-updates    +yes       +FIPS compliant crypto packages with stable security updates
      livepatch       +yes       +Canonical Livepatch service
      ros             +yes       +Security Updates for the Robot Operating System
      usg             +yes       +Security compliance and audit tools

      For a list of all Ubuntu Pro services, run 'pro status --all'

      This machine is not attached to an Ubuntu Pro subscription.
      See https://ubuntu.com/pro
      """
    When I verify root and non-root `pro status --all` calls have the same output
    And I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +AVAILABLE +DESCRIPTION
      anbox-cloud      +yes       +.*
      cc-eal           +no        +Common Criteria EAL2 Provisioning Packages
      esm-apps         +yes       +Expanded Security Maintenance for Applications
      esm-apps-legacy  +no        +Expanded Security Maintenance for Applications on Legacy Instances
      esm-infra        +yes       +Expanded Security Maintenance for Infrastructure
      esm-infra-legacy +no        +Expanded Security Maintenance for Infrastructure on Legacy Instances
      fips             +yes       +NIST-certified FIPS crypto packages
      fips-preview     +no        +.*
      fips-updates     +yes       +FIPS compliant crypto packages with stable security updates
      landscape        +no        +Management and administration tool for Ubuntu
      livepatch        +yes       +Canonical Livepatch service
      realtime-kernel  +no        +Ubuntu kernel with PREEMPT_RT patches integrated
      ros              +yes       +Security Updates for the Robot Operating System
      ros-updates      +no        +All Updates for the Robot Operating System
      usg              +yes       +Security compliance and audit tools

      This machine is not attached to an Ubuntu Pro subscription.
      See https://ubuntu.com/pro
      """
    When I append the following on uaclient config:
      """
      features:
          allow_beta: true
      """
    When I verify root and non-root `pro status` calls have the same output
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE         +AVAILABLE +DESCRIPTION
      anbox-cloud     +yes       +.*
      esm-apps        +yes       +Expanded Security Maintenance for Applications
      esm-infra       +yes       +Expanded Security Maintenance for Infrastructure
      fips            +yes       +NIST-certified FIPS crypto packages
      fips-updates    +yes       +FIPS compliant crypto packages with stable security updates
      livepatch       +yes       +Canonical Livepatch service
      ros             +yes       +Security Updates for the Robot Operating System
      usg             +yes       +Security compliance and audit tools

      FEATURES
      allow_beta: True

      For a list of all Ubuntu Pro services, run 'pro status --all'

      This machine is not attached to an Ubuntu Pro subscription.
      See https://ubuntu.com/pro
      """

    Examples: ubuntu release
      | release | machine_type  |
      | focal   | lxd-container |

  Scenario Outline: Unattached status in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I verify root and non-root `pro status` calls have the same output
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE         +AVAILABLE +DESCRIPTION
      anbox-cloud     +yes       +.*
      esm-apps        +yes       +Expanded Security Maintenance for Applications
      esm-infra       +yes       +Expanded Security Maintenance for Infrastructure
      fips-preview    +yes       +.*
      fips-updates    +yes       +FIPS compliant crypto packages with stable security updates
      livepatch       +yes       +Canonical Livepatch service
      realtime-kernel +yes       +Ubuntu kernel with PREEMPT_RT patches integrated
      usg             +yes       +Security compliance and audit tools

      For a list of all Ubuntu Pro services, run 'pro status --all'

      This machine is not attached to an Ubuntu Pro subscription.
      See https://ubuntu.com/pro
      """
    When I verify root and non-root `pro status --all` calls have the same output
    And I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +AVAILABLE +DESCRIPTION
      anbox-cloud      +yes       +.*
      cc-eal           +no        +Common Criteria EAL2 Provisioning Packages
      esm-apps         +yes       +Expanded Security Maintenance for Applications
      esm-apps-legacy  +no        +Expanded Security Maintenance for Applications on Legacy Instances
      esm-infra        +yes       +Expanded Security Maintenance for Infrastructure
      esm-infra-legacy +no        +Expanded Security Maintenance for Infrastructure on Legacy Instances
      fips             +no        +NIST-certified FIPS crypto packages
      fips-preview     +yes       +.*
      fips-updates     +yes       +FIPS compliant crypto packages with stable security updates
      landscape        +no        +Management and administration tool for Ubuntu
      livepatch        +yes       +Canonical Livepatch service
      realtime-kernel  +yes       +Ubuntu kernel with PREEMPT_RT patches integrated
      ros              +no        +Security Updates for the Robot Operating System
      ros-updates      +no        +All Updates for the Robot Operating System
      usg              +yes       +Security compliance and audit tools

      This machine is not attached to an Ubuntu Pro subscription.
      See https://ubuntu.com/pro
      """
    When I append the following on uaclient config:
      """
      features:
          allow_beta: true
      """
    When I verify root and non-root `pro status` calls have the same output
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE         +AVAILABLE +DESCRIPTION
      anbox-cloud     +yes       +.*
      esm-apps        +yes       +Expanded Security Maintenance for Applications
      esm-infra       +yes       +Expanded Security Maintenance for Infrastructure
      fips-preview    +yes       +.*
      fips-updates    +yes       +FIPS compliant crypto packages with stable security updates
      livepatch       +yes       +Canonical Livepatch service
      realtime-kernel +yes       +Ubuntu kernel with PREEMPT_RT patches integrated
      usg             +yes       +Security compliance and audit tools

      FEATURES
      allow_beta: True

      For a list of all Ubuntu Pro services, run 'pro status --all'

      This machine is not attached to an Ubuntu Pro subscription.
      See https://ubuntu.com/pro
      """

    Examples: ubuntu release
      | release | machine_type  |
      | jammy   | lxd-container |

  Scenario Outline: Unattached status in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I verify root and non-root `pro status` calls have the same output
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE         +AVAILABLE +DESCRIPTION
      anbox-cloud     +yes       +.*
      esm-apps        +yes       +Expanded Security Maintenance for Applications
      esm-infra       +yes       +Expanded Security Maintenance for Infrastructure
      landscape       +yes       +Management and administration tool for Ubuntu
      livepatch       +yes       +Canonical Livepatch service
      realtime-kernel +yes       +Ubuntu kernel with PREEMPT_RT patches integrated
      usg             +yes       +Security compliance and audit tools

      For a list of all Ubuntu Pro services, run 'pro status --all'

      This machine is not attached to an Ubuntu Pro subscription.
      See https://ubuntu.com/pro
      """
    When I verify root and non-root `pro status --all` calls have the same output
    And I run `pro status --all` as non-root
    Then stdout matches regexp:
      """
      SERVICE          +AVAILABLE +DESCRIPTION
      anbox-cloud      +yes       +.*
      cc-eal           +no        +Common Criteria EAL2 Provisioning Packages
      esm-apps         +yes       +Expanded Security Maintenance for Applications
      esm-apps-legacy  +no        +Expanded Security Maintenance for Applications on Legacy Instances
      esm-infra        +yes       +Expanded Security Maintenance for Infrastructure
      esm-infra-legacy +no        +Expanded Security Maintenance for Infrastructure on Legacy Instances
      fips             +no        +NIST-certified FIPS crypto packages
      fips-preview     +no        +.*
      fips-updates     +no        +FIPS compliant crypto packages with stable security updates
      landscape        +yes       +Management and administration tool for Ubuntu
      livepatch        +yes       +Canonical Livepatch service
      realtime-kernel  +yes       +Ubuntu kernel with PREEMPT_RT patches integrated
      ros              +no        +Security Updates for the Robot Operating System
      ros-updates      +no        +All Updates for the Robot Operating System
      usg              +yes       +Security compliance and audit tools

      This machine is not attached to an Ubuntu Pro subscription.
      See https://ubuntu.com/pro
      """
    When I append the following on uaclient config:
      """
      features:
          allow_beta: true
      """
    When I verify root and non-root `pro status` calls have the same output
    And I run `pro status` as non-root
    Then stdout matches regexp:
      """
      SERVICE         +AVAILABLE +DESCRIPTION
      anbox-cloud     +yes       +.*
      esm-apps        +yes       +Expanded Security Maintenance for Applications
      esm-infra       +yes       +Expanded Security Maintenance for Infrastructure
      landscape       +yes       +Management and administration tool for Ubuntu
      livepatch       +yes       +Canonical Livepatch service
      realtime-kernel +yes       +Ubuntu kernel with PREEMPT_RT patches integrated
      usg             +yes       +Security compliance and audit tools

      FEATURES
      allow_beta: True

      For a list of all Ubuntu Pro services, run 'pro status --all'

      This machine is not attached to an Ubuntu Pro subscription.
      See https://ubuntu.com/pro
      """

    Examples: ubuntu release
      | release | machine_type  |
      | noble   | lxd-container |

  @uses.config.contract_token
  Scenario Outline: Simulate status in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I do a preflight check for `contract_token` without the all flag
    Then stdout matches regexp:
      """
      SERVICE          +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
      (anbox-cloud     +yes       +.*)?
      ?cc-eal          +yes       +yes       +no           +Common Criteria EAL2 Provisioning Packages
      cis              +yes       +yes       +no           +Security compliance and audit tools
      esm-apps         +yes       +yes       +yes          +Expanded Security Maintenance for Applications
      esm-apps-legacy  +yes       +no        +no           +Expanded Security Maintenance for Applications on Legacy Instances
      esm-infra        +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
      esm-infra-legacy +yes       +no        +no           +Expanded Security Maintenance for Infrastructure on Legacy Instances
      fips             +yes       +yes       +no           +NIST-certified FIPS crypto packages
      fips-updates     +yes       +yes       +no           +FIPS compliant crypto packages with stable security updates
      livepatch        +yes       +yes       +yes          +Canonical Livepatch service
      ros              +yes       +yes       +no           +Security Updates for the Robot Operating System
      ros-updates      +yes       +yes       +no           +All Updates for the Robot Operating System
      """
    When I do a preflight check for `contract_token` with the all flag
    Then stdout matches regexp:
      """
      SERVICE          +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
      anbox-cloud      +(yes|no)  +.*
      cc-eal           +yes       +yes       +no           +Common Criteria EAL2 Provisioning Packages
      cis              +yes       +yes       +no           +Security compliance and audit tools
      esm-apps         +yes       +yes       +yes          +Expanded Security Maintenance for Applications
      esm-apps-legacy  +yes       +no        +no           +Expanded Security Maintenance for Applications on Legacy Instances
      esm-infra        +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
      esm-infra-legacy +yes       +no        +no           +Expanded Security Maintenance for Infrastructure on Legacy Instances
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

  @uses.config.contract_token
  Scenario Outline: Simulate status in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I do a preflight check for `contract_token` without the all flag
    Then stdout matches regexp:
      """
      SERVICE          +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
      (anbox-cloud     +yes       +.*)?
      ?cc-eal          +yes       +yes       +no           +Common Criteria EAL2 Provisioning Packages
      cis              +yes       +yes       +no           +Security compliance and audit tools
      esm-apps         +yes       +yes       +yes          +Expanded Security Maintenance for Applications
      esm-infra        +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
      fips             +yes       +yes       +no           +NIST-certified FIPS crypto packages
      fips-updates     +yes       +yes       +no           +FIPS compliant crypto packages with stable security updates
      livepatch        +yes       +yes       +yes          +Canonical Livepatch service
      ros              +yes       +yes       +no           +Security Updates for the Robot Operating System
      ros-updates      +yes       +yes       +no           +All Updates for the Robot Operating System
      """
    When I do a preflight check for `contract_token` with the all flag
    Then stdout matches regexp:
      """
      SERVICE          +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
      anbox-cloud      +(yes|no)  +.*
      cc-eal           +yes       +yes       +no           +Common Criteria EAL2 Provisioning Packages
      cis              +yes       +yes       +no           +Security compliance and audit tools
      esm-apps         +yes       +yes       +yes          +Expanded Security Maintenance for Applications
      esm-apps-legacy  +no        +no        +no           +Expanded Security Maintenance for Applications on Legacy Instances
      esm-infra        +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
      esm-infra-legacy +no        +no        +no           +Expanded Security Maintenance for Infrastructure on Legacy Instances
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
      | bionic  | lxd-container |

  @uses.config.contract_token
  Scenario Outline: Simulate status in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I do a preflight check for `contract_token` without the all flag
    Then stdout matches regexp:
      """
      SERVICE         +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
      anbox-cloud     +yes       +.*
      esm-apps        +yes       +yes       +yes          +Expanded Security Maintenance for Applications
      esm-infra       +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
      fips            +yes       +yes       +no           +NIST-certified FIPS crypto packages
      fips-updates    +yes       +yes       +no           +FIPS compliant crypto packages with stable security updates
      livepatch       +yes       +yes       +yes          +Canonical Livepatch service
      ros             +yes       +yes       +no           +Security Updates for the Robot Operating System
      usg             +yes       +yes       +no           +Security compliance and audit tools
      """
    When I do a preflight check for `contract_token` with the all flag
    Then stdout matches regexp:
      """
      SERVICE          +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
      anbox-cloud      +yes       +.*
      cc-eal           +no        +yes       +no           +Common Criteria EAL2 Provisioning Packages
      esm-apps         +yes       +yes       +yes          +Expanded Security Maintenance for Applications
      esm-apps-legacy  +no        +no        +no           +Expanded Security Maintenance for Applications on Legacy Instances
      esm-infra        +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
      esm-infra-legacy +no        +no        +no           +Expanded Security Maintenance for Infrastructure on Legacy Instances
      fips             +yes       +yes       +no           +NIST-certified FIPS crypto packages
      fips-preview     +no        +yes       +no           +.*
      fips-updates     +yes       +yes       +no           +FIPS compliant crypto packages with stable security updates
      landscape        +no        +yes       +no           +Management and administration tool for Ubuntu
      livepatch        +yes       +yes       +yes          +Canonical Livepatch service
      realtime-kernel  +no        +yes       +no           +Ubuntu kernel with PREEMPT_RT patches integrated
      ros              +yes       +yes       +no           +Security Updates for the Robot Operating System
      ros-updates      +no        +yes       +no           +All Updates for the Robot Operating System
      usg              +yes       +yes       +no           +Security compliance and audit tools
      """

    Examples: ubuntu release
      | release | machine_type  |
      | focal   | lxd-container |

  @uses.config.contract_token
  Scenario Outline: Simulate status in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I do a preflight check for `contract_token` without the all flag
    Then stdout matches regexp:
      """
      SERVICE         +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
      anbox-cloud     +yes       +.*
      esm-apps        +yes       +yes       +yes          +Expanded Security Maintenance for Applications
      esm-infra       +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
      fips-preview    +yes       +yes       +no           +.*
      fips-updates    +yes       +yes       +no           +FIPS compliant crypto packages with stable security updates
      livepatch       +yes       +yes       +yes          +Canonical Livepatch service
      realtime-kernel +yes       +yes       +no           +Ubuntu kernel with PREEMPT_RT patches integrated
      usg             +yes       +yes       +no           +Security compliance and audit tools
      """
    When I do a preflight check for `contract_token` with the all flag
    Then stdout matches regexp:
      """
      SERVICE          +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
      anbox-cloud      +yes       +.*
      cc-eal           +no        +yes       +no           +Common Criteria EAL2 Provisioning Packages
      esm-apps         +yes       +yes       +yes          +Expanded Security Maintenance for Applications
      esm-apps-legacy  +no        +no        +no           +Expanded Security Maintenance for Applications on Legacy Instances
      esm-infra        +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
      esm-infra-legacy +no        +no        +no           +Expanded Security Maintenance for Infrastructure on Legacy Instances
      fips             +no        +yes       +no           +NIST-certified FIPS crypto packages
      fips-preview     +yes       +yes       +no           +.*
      fips-updates     +yes       +yes       +no           +FIPS compliant crypto packages with stable security updates
      landscape        +no        +yes       +no           +Management and administration tool for Ubuntu
      livepatch        +yes       +yes       +yes          +Canonical Livepatch service
      realtime-kernel  +yes       +yes       +no           +Ubuntu kernel with PREEMPT_RT patches integrated
      ros              +no        +yes       +no           +Security Updates for the Robot Operating System
      ros-updates      +no        +yes       +no           +All Updates for the Robot Operating System
      usg              +yes       +yes       +no           +Security compliance and audit tools
      """

    Examples: ubuntu release
      | release | machine_type  |
      | jammy   | lxd-container |

  @uses.config.contract_token
  Scenario Outline: Simulate status in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I do a preflight check for `contract_token` without the all flag
    Then stdout matches regexp:
      """
      SERVICE         +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
      anbox-cloud     +yes       +.*
      esm-apps        +yes       +yes       +yes          +Expanded Security Maintenance for Applications
      esm-infra       +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
      landscape       +yes       +yes       +no           +Management and administration tool for Ubuntu
      livepatch       +yes       +yes       +yes          +Canonical Livepatch service
      realtime-kernel +yes       +yes       +no           +Ubuntu kernel with PREEMPT_RT patches integrated
      usg             +yes       +yes       +no           +Security compliance and audit tools
      """
    When I do a preflight check for `contract_token` with the all flag
    Then stdout matches regexp:
      """
      SERVICE          +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
      anbox-cloud      +yes       +.*
      cc-eal           +no        +yes       +no           +Common Criteria EAL2 Provisioning Packages
      esm-apps         +yes       +yes       +yes          +Expanded Security Maintenance for Applications
      esm-apps-legacy  +no        +no        +no           +Expanded Security Maintenance for Applications on Legacy Instances
      esm-infra        +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
      esm-infra-legacy +no        +no        +no           +Expanded Security Maintenance for Infrastructure on Legacy Instances
      fips             +no        +yes       +no           +NIST-certified FIPS crypto packages
      fips-preview     +no        +yes       +no           +.*
      fips-updates     +no        +yes       +no           +FIPS compliant crypto packages with stable security updates
      landscape        +yes       +yes       +no           +Management and administration tool for Ubuntu
      livepatch        +yes       +yes       +yes          +Canonical Livepatch service
      realtime-kernel  +yes       +yes       +no           +Ubuntu kernel with PREEMPT_RT patches integrated
      ros              +no        +yes       +no           +Security Updates for the Robot Operating System
      ros-updates      +no        +yes       +no           +All Updates for the Robot Operating System
      usg              +yes       +yes       +no           +Security compliance and audit tools
      """

    Examples: ubuntu release
      | release | machine_type  |
      | noble   | lxd-container |

  @uses.config.contract_token_staging_expired
  Scenario Outline: Simulate status with expired token in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `sed -i 's/contracts.can/contracts.staging.can/' /etc/ubuntu-advantage/uaclient.conf` with sudo
    And I verify that a preflight check for `contract_token_staging_expired` formatted as json exits 1
    Then stdout is a json matching the `ua_status` schema
    And stdout matches regexp:
      """
      \"result\": \"failure\"
      """
    And stdout matches regexp:
      """
      \"message\": \"Attach denied:\\nContract .* expired on .*\"
      """
    When I verify that a preflight check for `contract_token_staging_expired` formatted as yaml exits 1
    Then stdout is a yaml matching the `ua_status` schema
    Then stdout matches regexp:
      """
      errors:
      - message: 'Attach denied:

          Contract .* expired on .*
      """
    When I verify that a preflight check for `contract_token_staging_expired` without the all flag exits 1
    Then stdout matches regexp:
      """
      This token is not valid.
      Attach denied:
      Contract \".*\" expired on .*
      Visit https://ubuntu.com/pro/dashboard to manage contract tokens.

      SERVICE          +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
      (anbox-cloud     +(yes|no)       +.*)?
      ?cc-eal          +yes       +yes       +no           +Common Criteria EAL2 Provisioning Packages
      cis              +yes       +yes       +no           +Security compliance and audit tools
      esm-apps         +yes       +no        +no           +Expanded Security Maintenance for Applications
      esm-apps-legacy  +yes       +no        +no           +Expanded Security Maintenance for Applications on Legacy Instances
      esm-infra        +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
      esm-infra-legacy +yes       +no        +no           +Expanded Security Maintenance for Infrastructure on Legacy Instances
      fips             +yes       +yes       +no           +NIST-certified FIPS crypto packages
      fips-updates     +yes       +yes       +no           +FIPS compliant crypto packages with stable security updates
      livepatch        +yes       +yes       +yes          +Canonical Livepatch service
      ros              +yes       +no        +no           +Security Updates for the Robot Operating System
      ros-updates      +yes       +no        +no           +All Updates for the Robot Operating System
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |

  @uses.config.contract_token_staging_expired
  Scenario Outline: Simulate status with expired token in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `sed -i 's/contracts.can/contracts.staging.can/' /etc/ubuntu-advantage/uaclient.conf` with sudo
    And I verify that a preflight check for `contract_token_staging_expired` formatted as json exits 1
    Then stdout is a json matching the `ua_status` schema
    And stdout matches regexp:
      """
      \"result\": \"failure\"
      """
    And stdout matches regexp:
      """
      \"message\": \"Attach denied:\\nContract .* expired on .*\"
      """
    When I verify that a preflight check for `contract_token_staging_expired` formatted as yaml exits 1
    Then stdout is a yaml matching the `ua_status` schema
    Then stdout matches regexp:
      """
      errors:
      - message: 'Attach denied:

          Contract .* expired on .*
      """
    When I verify that a preflight check for `contract_token_staging_expired` without the all flag exits 1
    Then stdout matches regexp:
      """
      This token is not valid.
      Attach denied:
      Contract \".*\" expired on .*
      Visit https://ubuntu.com/pro/dashboard to manage contract tokens.

      SERVICE          +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
      (anbox-cloud     +(yes|no)       +.*)?
      ?cc-eal          +yes       +yes       +no           +Common Criteria EAL2 Provisioning Packages
      cis              +yes       +yes       +no           +Security compliance and audit tools
      esm-apps         +yes       +no        +no           +Expanded Security Maintenance for Applications
      esm-infra        +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
      fips             +yes       +yes       +no           +NIST-certified FIPS crypto packages
      fips-updates     +yes       +yes       +no           +FIPS compliant crypto packages with stable security updates
      livepatch        +yes       +yes       +yes          +Canonical Livepatch service
      ros              +yes       +no        +no           +Security Updates for the Robot Operating System
      ros-updates      +yes       +no        +no           +All Updates for the Robot Operating System
      """

    Examples: ubuntu release
      | release | machine_type  |
      | bionic  | lxd-container |

  @uses.config.contract_token_staging_expired
  Scenario Outline: Simulate status with expired token in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `sed -i 's/contracts.can/contracts.staging.can/' /etc/ubuntu-advantage/uaclient.conf` with sudo
    And I verify that a preflight check for `contract_token_staging_expired` formatted as json exits 1
    Then stdout is a json matching the `ua_status` schema
    And stdout matches regexp:
      """
      \"result\": \"failure\"
      """
    And stdout matches regexp:
      """
      \"message\": \"Attach denied:\\nContract .* expired on .*\"
      """
    When I verify that a preflight check for `contract_token_staging_expired` formatted as yaml exits 1
    Then stdout is a yaml matching the `ua_status` schema
    Then stdout matches regexp:
      """
      errors:
      - message: 'Attach denied:

          Contract .* expired on .*
      """
    When I verify that a preflight check for `contract_token_staging_expired` without the all flag exits 1
    Then stdout matches regexp:
      """
      This token is not valid.
      Attach denied:
      Contract \".*\" expired on .*
      Visit https://ubuntu.com/pro/dashboard to manage contract tokens.

      SERVICE         +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
      anbox-cloud     +yes       +.*
      esm-apps        +yes       +no        +no           +Expanded Security Maintenance for Applications
      esm-infra       +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
      fips            +yes       +yes       +no           +NIST-certified FIPS crypto packages
      fips-updates    +yes       +yes       +no           +FIPS compliant crypto packages with stable security updates
      livepatch       +yes       +yes       +yes          +Canonical Livepatch service
      ros             +yes       +no        +no           +Security Updates for the Robot Operating System
      usg             +yes       +yes       +no           +Security compliance and audit tools
      """

    Examples: ubuntu release
      | release | machine_type  |
      | focal   | lxd-container |

  @uses.config.contract_token_staging_expired
  Scenario Outline: Simulate status with expired token in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `sed -i 's/contracts.can/contracts.staging.can/' /etc/ubuntu-advantage/uaclient.conf` with sudo
    And I verify that a preflight check for `contract_token_staging_expired` formatted as json exits 1
    Then stdout is a json matching the `ua_status` schema
    And stdout matches regexp:
      """
      \"result\": \"failure\"
      """
    And stdout matches regexp:
      """
      \"message\": \"Attach denied:\\nContract .* expired on .*\"
      """
    When I verify that a preflight check for `contract_token_staging_expired` formatted as yaml exits 1
    Then stdout is a yaml matching the `ua_status` schema
    Then stdout matches regexp:
      """
      errors:
      - message: 'Attach denied:

          Contract .* expired on .*
      """
    When I verify that a preflight check for `contract_token_staging_expired` without the all flag exits 1
    Then stdout matches regexp:
      """
      This token is not valid.
      Attach denied:
      Contract \".*\" expired on .*
      Visit https://ubuntu.com/pro/dashboard to manage contract tokens.

      SERVICE         +AVAILABLE +ENTITLED  +AUTO_ENABLED +DESCRIPTION
      anbox-cloud     +yes       +.*
      esm-apps        +yes       +no        +no           +Expanded Security Maintenance for Applications
      esm-infra       +yes       +yes       +yes          +Expanded Security Maintenance for Infrastructure
      fips            +yes       +yes       +no           +NIST-certified FIPS crypto packages
      fips-preview    +yes       +yes       +no           +Preview of FIPS crypto packages undergoing certification with NIST
      fips-updates    +yes       +yes       +no           +.*
      livepatch       +yes       +yes       +yes          +Canonical Livepatch service
      """

    Examples: ubuntu release
      | release | machine_type  |
      | jammy   | lxd-container |

  Scenario Outline: Simulate status with invalid token
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I do a preflight check for `contract_token` formatted as json
    Then stdout is a json matching the `ua_status` schema
    When I do a preflight check for `contract_token` formatted as yaml
    Then stdout is a yaml matching the `ua_status` schema
    When I verify that a preflight check for `invalid_token` formatted as json exits 1
    Then stdout is a json matching the `ua_status` schema
    And API full output matches regexp:
      """
      {
        "environment_vars": [],
        "errors": [
          {
            "message": "Invalid token. See https://ubuntu.com/pro/dashboard",
            "message_code": "attach-invalid-token",
            "service": null,
            "type": "system"
          }
        ],
        "result": "failure",
        "services": [],
        "warnings": []
      }
      """
    When I verify that a preflight check for `invalid_token` formatted as yaml exits 1
    Then stdout is a yaml matching the `ua_status` schema
    And I will see the following on stdout:
      """
      environment_vars: []
      errors:
      - message: Invalid token. See https://ubuntu.com/pro/dashboard
        message_code: attach-invalid-token
        service: null
        type: system
      result: failure
      services: []
      warnings: []
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |

  Scenario Outline: Check notice file read permission
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `mkdir -p /run/ubuntu-advantage/notices` with sudo
    When I run `touch /run/ubuntu-advantage/notices/crasher` with sudo
    When I run `chmod 0 /run/ubuntu-advantage/notices/crasher` with sudo
    When I run `mkdir -p /var/lib/ubuntu-advantage/notices` with sudo
    When I run `touch /var/lib/ubuntu-advantage/notices/crasher` with sudo
    When I run `chmod 0 /var/lib/ubuntu-advantage/notices/crasher` with sudo
    When I run `touch /run/ubuntu-advantage/notices/10-reboot_required` with sudo
    When I run `pro status` as non-root
    Then stdout matches regexp:
      """
      NOTICES
      System reboot required
      """

    Examples: ubuntu release
      | release  | machine_type  |
      | xenial   | lxd-container |
      | bionic   | lxd-container |
      | focal    | lxd-container |
      | jammy    | lxd-container |
      | noble    | lxd-container |
      | oracular | lxd-container |
      | plucky   | lxd-container |

  Scenario Outline: Warn users not to redirect/pipe human readable output
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run shell command `pro version | cat` as non-root
    Then I will see the following on stderr
      """
      """
    When I run shell command `pro version > version_out` as non-root
    Then I will see the following on stderr
      """
      """
    When I run shell command `pro status | cat` as non-root
    Then I will see the following on stderr
      """
      WARNING: this output is intended to be human readable, and subject to change.
      In scripts, prefer using machine readable data from the `pro api` command,
      or use `pro status --format json`.
      """
    When I run shell command `pro status | cat` with sudo
    Then I will see the following on stderr
      """
      WARNING: this output is intended to be human readable, and subject to change.
      In scripts, prefer using machine readable data from the `pro api` command,
      or use `pro status --format json`.
      """
    When I run shell command `pro status > status_out` as non-root
    Then I will see the following on stderr
      """
      WARNING: this output is intended to be human readable, and subject to change.
      In scripts, prefer using machine readable data from the `pro api` command,
      or use `pro status --format json`.
      """
    When I run shell command `pro status > status_out` with sudo
    Then I will see the following on stderr
      """
      WARNING: this output is intended to be human readable, and subject to change.
      In scripts, prefer using machine readable data from the `pro api` command,
      or use `pro status --format json`.
      """
    When I run shell command `pro status --format tabular | cat` as non-root
    Then I will see the following on stderr
      """
      WARNING: this output is intended to be human readable, and subject to change.
      In scripts, prefer using machine readable data from the `pro api` command,
      or use `pro status --format json`.
      """
    When I run shell command `pro status --format tabular > status_out` as non-root
    Then I will see the following on stderr
      """
      WARNING: this output is intended to be human readable, and subject to change.
      In scripts, prefer using machine readable data from the `pro api` command,
      or use `pro status --format json`.
      """
    When I run shell command `pro status --format json | cat` as non-root
    Then I will see the following on stderr
      """
      """
    When I run shell command `pro status --format json > status_out` as non-root
    Then I will see the following on stderr
      """
      """
    # populate esm-cache
    When I apt update
    And I run shell command `pro security-status | cat` as non-root
    Then I will see the following on stderr
      """
      WARNING: this output is intended to be human readable, and subject to change.
      In scripts, prefer using machine readable data from the `pro api` command,
      or use `pro security-status --format json`.
      """
    When I run shell command `pro security-status > status_out` as non-root
    Then I will see the following on stderr
      """
      WARNING: this output is intended to be human readable, and subject to change.
      In scripts, prefer using machine readable data from the `pro api` command,
      or use `pro security-status --format json`.
      """
    When I run shell command `pro security-status --format json | cat` as non-root
    Then I will see the following on stderr
      """
      """
    When I run shell command `pro security-status --format json > status_out` as non-root
    Then I will see the following on stderr
      """
      """

    Examples: ubuntu release
      | release  | machine_type  |
      | xenial   | lxd-container |
      | bionic   | lxd-container |
      | focal    | lxd-container |
      | jammy    | lxd-container |
      | noble    | lxd-container |
      | oracular | lxd-container |
      | plucky   | lxd-container |
