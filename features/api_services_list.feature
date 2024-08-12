Feature: Services list api

  @uses.config.contract_token
  Scenario Outline: Get services list when unattached/attached as non-root
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro api u.pro.services.list.v1` as non-root
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "services": [
            {
              "available": true,
              "description": "Scalable Android in the cloud",
              "entitled": null,
              "name": "anbox-cloud"
            },
            {
              "available": false,
              "description": "Common Criteria EAL2 Provisioning Packages",
              "entitled": null,
              "name": "cc-eal"
            },
            {
              "available": false,
              "description": "Security compliance and audit tools",
              "entitled": null,
              "name": "usg"
            },
            {
              "available": true,
              "description": "Expanded Security Maintenance for Applications",
              "entitled": null,
              "name": "esm-apps"
            },
            {
              "available": true,
              "description": "Expanded Security Maintenance for Infrastructure",
              "entitled": null,
              "name": "esm-infra"
            },
            {
              "available": false,
              "description": "NIST-certified FIPS crypto packages",
              "entitled": null,
              "name": "fips"
            },
            {
              "available": false,
              "description": "Preview of FIPS crypto packages undergoing certification with NIST",
              "entitled": null,
              "name": "fips-preview"
            },
            {
              "available": false,
              "description": "FIPS compliant crypto packages with stable security updates",
              "entitled": null,
              "name": "fips-updates"
            },
            {
              "available": true,
              "description": "Management and administration tool for Ubuntu",
              "entitled": null,
              "name": "landscape"
            },
            {
              "available": true,
              "description": "Canonical Livepatch service",
              "entitled": null,
              "name": "livepatch"
            },
            {
              "available": true,
              "description": "Ubuntu kernel with PREEMPT_RT patches integrated",
              "entitled": null,
              "name": "realtime-kernel"
            },
            {
              "available": false,
              "description": "Security Updates for the Robot Operating System",
              "entitled": null,
              "name": "ros"
            },
            {
              "available": false,
              "description": "All Updates for the Robot Operating System",
              "entitled": null,
              "name": "ros-updates"
            }
          ]
        },
        "meta": {
          "environment_vars": []
        },
        "type": "ServicesList"
      }
      """
    When I attach `contract_token` with sudo
    And I run `pro api u.pro.services.list.v1` as non-root
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "services": [
            {
              "available": true,
              "description": "Scalable Android in the cloud",
              "entitled": true,
              "name": "anbox-cloud"
            },
            {
              "available": false,
              "description": "Common Criteria EAL2 Provisioning Packages",
              "entitled": true,
              "name": "cc-eal"
            },
            {
              "available": true,
              "description": "Expanded Security Maintenance for Applications",
              "entitled": true,
              "name": "esm-apps"
            },
            {
              "available": true,
              "description": "Expanded Security Maintenance for Infrastructure",
              "entitled": true,
              "name": "esm-infra"
            },
            {
              "available": false,
              "description": "NIST-certified FIPS crypto packages",
              "entitled": true,
              "name": "fips"
            },
            {
              "available": false,
              "description": "Preview of FIPS crypto packages undergoing certification with NIST",
              "entitled": true,
              "name": "fips-preview"
            },
            {
              "available": false,
              "description": "FIPS compliant crypto packages with stable security updates",
              "entitled": true,
              "name": "fips-updates"
            },
            {
              "available": true,
              "description": "Management and administration tool for Ubuntu",
              "entitled": true,
              "name": "landscape"
            },
            {
              "available": true,
              "description": "Canonical Livepatch service",
              "entitled": true,
              "name": "livepatch"
            },
            {
              "available": true,
              "description": "Ubuntu kernel with PREEMPT_RT patches integrated",
              "entitled": true,
              "name": "realtime-kernel"
            },
            {
              "available": false,
              "description": "Security Updates for the Robot Operating System",
              "entitled": true,
              "name": "ros"
            },
            {
              "available": false,
              "description": "All Updates for the Robot Operating System",
              "entitled": true,
              "name": "ros-updates"
            },
            {
              "available": false,
              "description": "Security compliance and audit tools",
              "entitled": true,
              "name": "usg"
            }
          ]
        },
        "meta": {
          "environment_vars": []
        },
        "type": "ServicesList"
      }
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |

  @uses.config.contract_token
  Scenario Outline: Get services list when unattached/attached as root
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro api u.pro.services.list.v1` with sudo
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "services": [
            {
              "available": true,
              "description": "Scalable Android in the cloud",
              "entitled": null,
              "name": "anbox-cloud"
            },
            {
              "available": false,
              "description": "Common Criteria EAL2 Provisioning Packages",
              "entitled": null,
              "name": "cc-eal"
            },
            {
              "available": false,
              "description": "Security compliance and audit tools",
              "entitled": null,
              "name": "usg"
            },
            {
              "available": true,
              "description": "Expanded Security Maintenance for Applications",
              "entitled": null,
              "name": "esm-apps"
            },
            {
              "available": true,
              "description": "Expanded Security Maintenance for Infrastructure",
              "entitled": null,
              "name": "esm-infra"
            },
            {
              "available": false,
              "description": "NIST-certified FIPS crypto packages",
              "entitled": null,
              "name": "fips"
            },
            {
              "available": false,
              "description": "Preview of FIPS crypto packages undergoing certification with NIST",
              "entitled": null,
              "name": "fips-preview"
            },
            {
              "available": false,
              "description": "FIPS compliant crypto packages with stable security updates",
              "entitled": null,
              "name": "fips-updates"
            },
            {
              "available": true,
              "description": "Management and administration tool for Ubuntu",
              "entitled": null,
              "name": "landscape"
            },
            {
              "available": true,
              "description": "Canonical Livepatch service",
              "entitled": null,
              "name": "livepatch"
            },
            {
              "available": true,
              "description": "Ubuntu kernel with PREEMPT_RT patches integrated",
              "entitled": null,
              "name": "realtime-kernel"
            },
            {
              "available": false,
              "description": "Security Updates for the Robot Operating System",
              "entitled": null,
              "name": "ros"
            },
            {
              "available": false,
              "description": "All Updates for the Robot Operating System",
              "entitled": null,
              "name": "ros-updates"
            }
          ]
        },
        "meta": {
          "environment_vars": []
        },
        "type": "ServicesList"
      }
      """
    When I attach `contract_token` with sudo
    And I run `pro api u.pro.services.list.v1` with sudo
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "services": [
            {
              "available": true,
              "description": "Scalable Android in the cloud",
              "entitled": true,
              "name": "anbox-cloud"
            },
            {
              "available": false,
              "description": "Common Criteria EAL2 Provisioning Packages",
              "entitled": true,
              "name": "cc-eal"
            },
            {
              "available": true,
              "description": "Expanded Security Maintenance for Applications",
              "entitled": true,
              "name": "esm-apps"
            },
            {
              "available": true,
              "description": "Expanded Security Maintenance for Infrastructure",
              "entitled": true,
              "name": "esm-infra"
            },
            {
              "available": false,
              "description": "NIST-certified FIPS crypto packages",
              "entitled": true,
              "name": "fips"
            },
            {
              "available": false,
              "description": "Preview of FIPS crypto packages undergoing certification with NIST",
              "entitled": true,
              "name": "fips-preview"
            },
            {
              "available": false,
              "description": "FIPS compliant crypto packages with stable security updates",
              "entitled": true,
              "name": "fips-updates"
            },
            {
              "available": true,
              "description": "Management and administration tool for Ubuntu",
              "entitled": true,
              "name": "landscape"
            },
            {
              "available": true,
              "description": "Canonical Livepatch service",
              "entitled": true,
              "name": "livepatch"
            },
            {
              "available": true,
              "description": "Ubuntu kernel with PREEMPT_RT patches integrated",
              "entitled": true,
              "name": "realtime-kernel"
            },
            {
              "available": false,
              "description": "Security Updates for the Robot Operating System",
              "entitled": true,
              "name": "ros"
            },
            {
              "available": false,
              "description": "All Updates for the Robot Operating System",
              "entitled": true,
              "name": "ros-updates"
            },
            {
              "available": false,
              "description": "Security compliance and audit tools",
              "entitled": true,
              "name": "usg"
            }
          ]
        },
        "meta": {
          "environment_vars": []
        },
        "type": "ServicesList"
      }
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |
