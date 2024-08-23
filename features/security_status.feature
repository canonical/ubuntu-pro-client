Feature: Security status command behavior

  @perf
  Scenario Outline: Profile unattached security-status
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I apt update
    And I apt install `ansible`
    And I set up parca-agent 2
    And I run `pro security-status` as non-root `100` times

    Examples: ubuntu release
      | release | machine_type | package | service  |
      | jammy   | lxd-vm       | ansible | esm-apps |
