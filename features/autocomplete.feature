Feature: Pro autocomplete commands

  # Side effect: this verifies that `ua` still works as a command
  Scenario Outline: Verify autocomplete options
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I prepare the autocomplete test
    And I press tab twice to autocomplete the `ua` command
    Then stdout matches regexp:
      """
      --debug    +auto-attach   +enable   +status\r
      --help     +collect-logs  +fix      +system\r
      --version  +config        +help     +version\r
      api        +detach        +refresh  +\r
      attach     +disable       +security-status
      """
    When I press tab twice to autocomplete the `pro` command
    Then stdout matches regexp:
      """
      --debug    +auto-attach   +enable   +status\r
      --help     +collect-logs  +fix      +system\r
      --version  +config        +help     +version\r
      api        +detach        +refresh  +\r
      attach     +disable       +security-status
      """
    When I press tab twice to autocomplete the `ua enable` command
    Then stdout matches regexp:
      """
      anbox-cloud +esm-infra    +livepatch       +usg\s*
      cc-eal      +fips         +realtime-kernel\s*
      cis         +fips-updates +ros\s*
      esm-apps    +landscape    +ros-updates\s*
      """
    When I press tab twice to autocomplete the `pro enable` command
    Then stdout matches regexp:
      """
      anbox-cloud +esm-infra    +livepatch       +usg\s*
      cc-eal      +fips         +realtime-kernel\s*
      cis         +fips-updates +ros\s*
      esm-apps    +landscape    +ros-updates\s*
      """
    When I press tab twice to autocomplete the `ua disable` command
    Then stdout matches regexp:
      """
      anbox-cloud +esm-infra    +livepatch       +usg\s*
      cc-eal      +fips         +realtime-kernel\s*
      cis         +fips-updates +ros\s*
      esm-apps    +landscape    +ros-updates\s*
      """
    When I press tab twice to autocomplete the `pro disable` command
    Then stdout matches regexp:
      """
      anbox-cloud +esm-infra    +livepatch       +usg\s*
      cc-eal      +fips         +realtime-kernel\s*
      cis         +fips-updates +ros\s*
      esm-apps    +landscape    +ros-updates\s*
      """

    Examples: ubuntu release
      | release  | machine_type  |
      # | xenial  | lxd-container | Can't rely on Xenial because of bash sorting things weirdly
      | bionic   | lxd-container |
      | focal    | lxd-container |
      | jammy    | lxd-container |
      | noble    | lxd-container |
      | oracular | lxd-container |
