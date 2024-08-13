Feature: Pro is expected version

  @uses.config.check_version
  Scenario Outline: Check pro version
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `dpkg-query --showformat='${Version}' --show ubuntu-pro-client` with sudo
    Then I will see the following on stdout
      """
      $behave_var{version}
      """
    When I run `pro version` with sudo
    Then I will see the following on stdout
      """
      $behave_var{version}
      """
    # The following doesn't actually assert anything. It merely ensures that the output of
    # apt-cache policy ubuntu-pro-client on the test machine is included in our test output.
    # This is useful to manually verify the package is installed from the correct source e.g. -proposed.
    When I check the apt-cache policy of ubuntu-pro-client
    Then the apt-cache policy of ubuntu-pro-client is
      """
      THIS GETS REPLACED AT RUNTIME VIA A HACK IN steps/ubuntu_advantage_tools.py
      """

    Examples: version
      | release  | machine_type   |
      | xenial   | lxd-container  |
      | xenial   | lxd-vm         |
      | xenial   | aws.generic    |
      | xenial   | aws.pro        |
      | xenial   | aws.pro-fips   |
      | xenial   | azure.generic  |
      | xenial   | azure.pro      |
      | xenial   | azure.pro-fips |
      | xenial   | gcp.generic    |
      | xenial   | gcp.pro        |
      | xenial   | gcp.pro-fips   |
      | bionic   | lxd-container  |
      | bionic   | lxd-vm         |
      | bionic   | aws.generic    |
      | bionic   | aws.pro        |
      | bionic   | aws.pro-fips   |
      | bionic   | azure.generic  |
      | bionic   | azure.pro      |
      | bionic   | azure.pro-fips |
      | bionic   | gcp.generic    |
      | bionic   | gcp.pro        |
      | bionic   | gcp.pro-fips   |
      | focal    | lxd-container  |
      | focal    | lxd-vm         |
      | focal    | aws.generic    |
      | focal    | aws.pro        |
      | focal    | aws.pro-fips   |
      | focal    | azure.generic  |
      | focal    | azure.pro      |
      | focal    | azure.pro-fips |
      | focal    | gcp.generic    |
      | focal    | gcp.pro        |
      | focal    | gcp.pro-fips   |
      | jammy    | lxd-container  |
      | jammy    | lxd-vm         |
      | jammy    | aws.generic    |
      | jammy    | aws.pro        |
      | jammy    | aws.pro-fips   |
      | jammy    | azure.generic  |
      | jammy    | azure.pro      |
      | jammy    | azure.pro-fips |
      | jammy    | gcp.generic    |
      | jammy    | gcp.pro        |
      | jammy    | gcp.pro-fips   |
      | noble    | lxd-container  |
      | noble    | lxd-vm         |
      | noble    | aws.generic    |
      | noble    | aws.pro        |
      | noble    | aws.pro-fips   |
      | noble    | azure.generic  |
      | noble    | azure.pro      |
      | noble    | azure.pro-fips |
      | noble    | gcp.generic    |
      | noble    | gcp.pro        |
      | noble    | gcp.pro-fips   |
      # no oracular on clouds yet - add it when those are available
      | oracular | lxd-container  |
      | oracular | lxd-vm         |

  @uses.config.check_version @upgrade
  Scenario Outline: Check pro version
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `dpkg-query --showformat='${Version}' --show ubuntu-pro-client` with sudo
    Then I will see the following on stdout
      """
      $behave_var{version}
      """
    When I run `pro version` with sudo
    Then I will see the following on stdout
      """
      $behave_var{version}
      """
    # The following doesn't actually assert anything. It merely ensures that the output of
    # apt-cache policy ubuntu-pro-client on the test machine is included in our test output.
    # This is useful to manually verify the package is installed from the correct source e.g. -proposed.
    When I check the apt-cache policy of ubuntu-pro-client
    Then the apt-cache policy of ubuntu-pro-client is
      """
      THIS GETS REPLACED AT RUNTIME VIA A HACK IN steps/ubuntu_advantage_tools.py
      """

    Examples: version
      | release  | machine_type  |
      | xenial   | lxd-container |
      | bionic   | lxd-container |
      | focal    | lxd-container |
      | jammy    | lxd-container |
      | noble    | lxd-container |
      | oracular | lxd-container |

  @uses.config.contract_token
  Scenario Outline: Attached show version in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I run `pro version` as non-root
    Then I will see the uaclient version on stdout
    When I run `pro version` with sudo
    Then I will see the uaclient version on stdout
    When I run `pro --version` as non-root
    Then I will see the uaclient version on stdout
    When I run `pro --version` with sudo
    Then I will see the uaclient version on stdout

    Examples: ubuntu release
      | release  | machine_type  |
      | bionic   | lxd-container |
      | focal    | lxd-container |
      | xenial   | lxd-container |
      | jammy    | lxd-container |
      | noble    | lxd-container |
      | oracular | lxd-container |

  Scenario Outline: Check for newer versions of the client in an ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    # Make sure we have a fresh, just rebooted, environment
    When I reboot the machine
    Then I verify that no files exist matching `/run/ubuntu-advantage/candidate-version`
    When I run `pro status` with sudo
    Then stderr does not match regexp:
      """
      .*\[info\].* A new version is available: 2:99.9.9
      Please run:
          sudo apt install ubuntu-pro-client
      to get the latest bug fixes and new features.
      """
    And I verify that files exist matching `/run/ubuntu-advantage/candidate-version`
    # We forge a candidate to see results
    When I delete the file `/run/ubuntu-advantage/candidate-version`
    And I create the file `/run/ubuntu-advantage/candidate-version` with the following
      """
      2:99.9.9
      """
    And I run `pro status` as non-root
    Then stderr matches regexp:
      """
      .*\[info\].* A new version is available: 2:99.9.9
      Please run:
          sudo apt install ubuntu-pro-client
      to get the latest bug fixes and new features.
      """
    When I run `pro status --format json` as non-root
    Then stderr does not match regexp:
      """
      .*\[info\].* A new version is available: 2:99.9.9
      Please run:
          sudo apt install ubuntu-pro-client
      to get the latest bug fixes and new features.
      """
    When I run `pro config show` as non-root
    Then stderr matches regexp:
      """
      .*\[info\].* A new version is available: 2:99.9.9
      Please run:
          sudo apt install ubuntu-pro-client
      to get the latest bug fixes and new features.
      """
    When I run `pro api u.pro.version.v1` as non-root
    Then stdout matches regexp
      """
      \"code\": \"new-version-available\"
      """
    When I verify that running `pro api u.pro.version.inexistent` `as non-root` exits `1`
    Then stdout matches regexp
      """
      \"code\": \"new-version-available\"
      """
    When I run `pro api u.pro.version.v1` as non-root
    Then stderr does not match regexp:
      """
      .*\[info\].* A new version is available: 2:99.9.9
      Please run:
          sudo apt install ubuntu-pro-client
      to get the latest bug fixes and new features.
      """
    When I apt update
    # The update will bring a new candidate, which is the current installed version
    And I run `pro status` as non-root
    Then stderr does not match regexp:
      """
      .*\[info\].* A new version is available: 2:99.9.9
      Please run:
          sudo apt install ubuntu-pro-client
      to get the latest bug fixes and new features.
      """

    Examples: ubuntu release
      | release  | machine_type  |
      | xenial   | lxd-container |
      | bionic   | lxd-container |
      | focal    | lxd-container |
      | jammy    | lxd-container |
      | noble    | lxd-container |
      | oracular | lxd-container |
