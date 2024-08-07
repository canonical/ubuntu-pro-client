@uses.config.contract_token
Feature: Enable ROS on ubuntu

  Scenario Outline: Attached enable ros on a machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then I verify that `ros` is disabled
    When I run `pro enable ros --assume-yes` with sudo
    Then I verify that `ros` is enabled
    And I verify that `esm-apps` is enabled
    And I verify that `esm-infra` is enabled
    When I verify that running `pro disable esm-apps` `with sudo` and stdin `N` exits `1`
    Then stdout matches regexp
      """
      ROS ESM Security Updates depends on Ubuntu Pro: ESM Apps.
      Disable ROS ESM Security Updates and proceed to disable Ubuntu Pro: ESM Apps\? \(y\/N\) Cannot disable Ubuntu Pro: ESM Apps when ROS ESM Security Updates is enabled.
      """
    When I run `pro disable esm-apps` `with sudo` and stdin `y`
    Then stdout matches regexp
      """
      ROS ESM Security Updates depends on Ubuntu Pro: ESM Apps.
      Disable ROS ESM Security Updates and proceed to disable Ubuntu Pro: ESM Apps\? \(y\/N\) Disabling dependent service: ROS ESM Security Updates
      Removing APT access to ROS ESM Security Updates
      Updating package lists
      Removing APT access to Ubuntu Pro: ESM Apps
      Updating package lists
      """
    And I verify that `ros` is disabled
    And I verify that `esm-apps` is disabled
    When I verify that running `pro enable ros` `with sudo` and stdin `N` exits `1`
    Then stdout matches regexp
      """
      ROS ESM Security Updates cannot be enabled with Ubuntu Pro: ESM Apps disabled.
      Enable Ubuntu Pro: ESM Apps and proceed to enable ROS ESM Security Updates\? \(y\/N\) Cannot enable ROS ESM Security Updates when Ubuntu Pro: ESM Apps is disabled.
      """
    When I run `pro enable ros` `with sudo` and stdin `y`
    Then stdout matches regexp
      """
      One moment, checking your subscription first
      ROS ESM Security Updates cannot be enabled with Ubuntu Pro: ESM Apps disabled.
      Enable Ubuntu Pro: ESM Apps and proceed to enable ROS ESM Security Updates\? \(y\/N\) Enabling required service: Ubuntu Pro: ESM Apps
      Configuring APT access to Ubuntu Pro: ESM Apps
      Updating Ubuntu Pro: ESM Apps package lists
      Configuring APT access to ROS ESM Security Updates
      Updating ROS ESM Security Updates package lists
      ROS ESM Security Updates enabled
      """
    And I verify that `ros` is enabled
    And I verify that `esm-apps` is enabled
    And I verify that `esm-infra` is enabled
    When I run `apt-cache policy` as non-root
    Then apt-cache policy for the following url has priority `500`
      """
      <ros-security-source> amd64 Packages
      """
    When I apt install `python3-catkin-pkg`
    Then I verify that `python3-catkin-pkg` is installed from apt source `<ros-security-source>`
    When I run `pro enable ros-updates --assume-yes` with sudo
    Then I verify that `ros-updates` is enabled
    When I run `apt-cache policy` as non-root
    Then apt-cache policy for the following url has priority `500`
      """
      <ros-updates-source> amd64 Packages
      """
    When I apt install `python3-catkin-pkg`
    Then I verify that `python3-catkin-pkg` is installed from apt source `<ros-updates-source>`
    When I run `pro disable ros` `with sudo` and stdin `y`
    Then stdout matches regexp
      """
      ROS ESM All Updates depends on ROS ESM Security Updates.
      Disable ROS ESM All Updates and proceed to disable ROS ESM Security Updates\? \(y\/N\) Disabling dependent service: ROS ESM All Updates
      Removing APT access to ROS ESM All Updates
      Updating package lists
      Removing APT access to ROS ESM Security Updates
      Updating package lists
      """
    And I verify that `ros-updates` is disabled
    When I run `pro enable ros-updates` `with sudo` and stdin `y`
    Then stdout matches regexp
      """
      One moment, checking your subscription first
      ROS ESM All Updates cannot be enabled with ROS ESM Security Updates disabled.
      Enable ROS ESM Security Updates and proceed to enable ROS ESM All Updates\? \(y\/N\) Enabling required service: ROS ESM Security Updates
      Configuring APT access to ROS ESM Security Updates
      Updating ROS ESM Security Updates package lists
      Configuring APT access to ROS ESM All Updates
      Updating ROS ESM All Updates package lists
      ROS ESM All Updates enabled
      """
    And I verify that `ros-updates` is enabled
    And I verify that `ros` is enabled
    When I run `pro disable ros-updates --assume-yes` with sudo
    And I run `pro disable ros --assume-yes` with sudo
    And I run `pro disable esm-apps --assume-yes` with sudo
    And I run `pro disable esm-infra --assume-yes` with sudo
    And I run `pro enable ros-updates --assume-yes` with sudo
    Then I verify that `ros-updates` is enabled
    And I verify that `ros` is enabled
    And I verify that `esm-apps` is enabled
    And I verify that `esm-infra` is enabled
    When I run `pro detach` `with sudo` and stdin `y`
    Then stdout matches regexp:
      """
      Removing APT access to ROS ESM All Updates
      Updating package lists
      Removing APT access to ROS ESM Security Updates
      Updating package lists
      Removing APT access to Ubuntu Pro: ESM Apps
      Updating package lists
      Removing APT access to Ubuntu Pro: ESM Infra
      Updating package lists
      This machine is now detached.
      """
    And the machine is unattached

    Examples: ubuntu release
      | release | machine_type  | ros-security-source                                    | ros-updates-source                                            |
      | xenial  | lxd-container | https://esm.ubuntu.com/ros/ubuntu xenial-security/main | https://esm.ubuntu.com/ros-updates/ubuntu xenial-updates/main |
      | bionic  | lxd-container | https://esm.ubuntu.com/ros/ubuntu bionic-security/main | https://esm.ubuntu.com/ros-updates/ubuntu bionic-updates/main |
      | bionic  | wsl           | https://esm.ubuntu.com/ros/ubuntu bionic-security/main | https://esm.ubuntu.com/ros-updates/ubuntu bionic-updates/main |
