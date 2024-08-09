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

    Examples: ubuntu release
      | release | machine_type  |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | xenial  | lxd-container |
      | jammy   | lxd-container |
      | mantic  | lxd-container |
      | noble   | lxd-container |
