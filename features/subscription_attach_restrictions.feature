@uses.config.contract_token
Feature: One time pro subscription related tests

  Scenario Outline: Attach fail if subscription is restricted to release
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I set the machine token overlay to the following yaml:
      """
      machineTokenInfo:
          contractInfo:
              resourceEntitlements:
                  - type: support
                    affordances:
                        onlySeries: <onlyseries>
      """
    When I attach `contract_token` with sudo
    Then stderr contains substring:
      """
      Attaching to this contract is only allowed on the Ubuntu <onlyseries> <onlyrelease> release
      """
    And the machine is unattached

    Examples: ubuntu release
      | release | machine_type  | onlyseries | onlyrelease |
      | xenial  | lxd-container | bionic     | 18.04       |
      | bionic  | lxd-container | xenial     | 16.04       |
      | focal   | lxd-container | noble      | 24.04       |
      | jammy   | lxd-container | focal      | 20.04       |
      | noble   | lxd-container | jammy      | 22.04       |

  Scenario Outline: check notice visible when attached with onlySeries present
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I set the machine token overlay to the following yaml:
      """
      machineTokenInfo:
          contractInfo:
              resourceEntitlements:
                  - type: support
                    affordances:
                        onlySeries: <onlyseries>
      """
    When I attach `contract_token` with sudo
    Then the machine is attached
    When I run `pro status` with sudo
    Then stdout contains substring:
      """
      Limited to release: Ubuntu <onlyseries>
      """

    Examples: ubuntu release
      | release | machine_type  | onlyseries |
      | xenial  | lxd-container | xenial     |
      | bionic  | lxd-container | bionic     |
      | focal   | lxd-container | focal      |
      | jammy   | lxd-container | jammy      |
      | noble   | lxd-container | noble      |
