@uses.config.contract_token
Feature: Attached cloud does not detach when auto-attaching after manually attaching

  Scenario Outline: No detaching on manually attached machine on all clouds
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I run `pro refresh` with sudo
    Then I will see the following on stdout:
      """
      Successfully processed your pro configuration.
      Successfully refreshed your subscription.
      Successfully updated Ubuntu Pro related APT and MOTD messages.
      """
    When I verify that running `pro auto-attach` `with sudo` exits `2`
    Then stderr matches regexp:
      """
      This machine is already attached to '.+'
      To use a different subscription first run: sudo pro detach.
      """
    And I verify that `esm-infra` is enabled

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | aws.generic   |
      | xenial  | azure.generic |
      | xenial  | gcp.generic   |
      | bionic  | aws.generic   |
      | bionic  | azure.generic |
      | bionic  | gcp.generic   |
      | focal   | aws.generic   |
      | focal   | azure.generic |
      | focal   | gcp.generic   |
      | noble   | aws.generic   |
      | noble   | azure.generic |
      | noble   | gcp.generic   |
