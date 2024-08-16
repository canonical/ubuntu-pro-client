Feature: u.pro.services.disable

  Scenario Outline: u.pro.services.disable.v1 container services
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I apt update
    # Requires attach
    When I verify that running `pro api u.pro.services.disable.v1 --args service=esm-infra` `with sudo` exits `1`
    Then API errors field output is:
      """
      [
        {
          "code": "unattached",
          "meta": {},
          "title": "This machine is not attached to an Ubuntu Pro subscription.\nSee https://ubuntu.com/pro"
        }
      ]
      """
    When I attach `contract_token` with sudo
    # Requires root
    When I verify that running `pro api u.pro.services.disable.v1 --args service=esm-infra` `as non-root` exits `1`
    Then API errors field output is:
      """
      [
        {
          "code": "nonroot-user",
          "meta": {},
          "title": "This command must be run as root (try using sudo)."
        }
      ]
      """
    # Invalid service name
    When I verify that running `pro api u.pro.services.disable.v1 --args service=invalid` `with sudo` exits `1`
    Then API errors field output is:
      """
      [
        {
          "code": "entitlement-not-found",
          "meta": {
            "entitlement_name": "invalid"
          },
          "title": "could not find entitlement named \"invalid\""
        }
      ]
      """
    # Basic disable
    When I run `pro api u.pro.services.disable.v1 --args service=esm-infra` with sudo
    Then API data field output is:
      """
      {
        "attributes": {
          "disabled": [
            "esm-infra"
          ]
        },
        "meta": {
          "environment_vars": []
        },
        "type": "DisableService"
      }
      """
    Then I verify that `esm-infra` is disabled
    # Disable already disabled service succeeds
    When I run `pro api u.pro.services.disable.v1 --args service=esm-infra` with sudo
    Then API data field output is:
      """
      {
        "attributes": {
          "disabled": []
        },
        "meta": {
          "environment_vars": []
        },
        "type": "DisableService"
      }
      """
    # disables dependent services
    When I run `pro enable ros-updates --assume-yes` with sudo
    When I run `pro api u.pro.services.disable.v1 --args service=esm-apps` with sudo
    Then API data field output is:
      """
      {
        "attributes": {
          "disabled": [
            "esm-apps",
            "ros",
            "ros-updates"
          ]
        },
        "meta": {
          "environment_vars": []
        },
        "type": "DisableService"
      }
      """
    # purge works and post enable messages work
    When I apt install `curl`
    When I run `apt-cache policy curl` as non-root
    Then stdout matches regexp:
      """
      \*\*\* <curl_version>\+esm.* 510
      """
    When I run `pro api u.pro.services.disable.v1 --data '{"service": "esm-infra", "purge": true}'` with sudo
    Then API data field output is:
      """
      {
        "attributes": {
          "disabled": [
            "esm-infra"
          ]
        },
        "meta": {
          "environment_vars": []
        },
        "type": "DisableService"
      }
      """
    When I run `apt-cache policy curl` as non-root
    Then stdout contains substring:
      """
      *** <curl_version> 500
      """

    Examples:
      | release | machine_type  | curl_version       |
      | xenial  | lxd-container | 7.47.0-1ubuntu2.19 |
      | bionic  | lxd-container | 7.58.0-2ubuntu3.24 |

  Scenario Outline: u.pro.services.disable.v1 vm services
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I apt update
    And I attach `contract_token` with sudo
    # Basic disable
    And I run `pro api u.pro.services.disable.v1 --args service=livepatch` with sudo
    Then API data field output is:
      """
      {
        "attributes": {
          "disabled": [
            "livepatch"
          ]
        },
        "meta": {
          "environment_vars": []
        },
        "type": "DisableService"
      }
      """
    # fails when purge not supported
    When I run `pro enable realtime-kernel --access-only` with sudo
    When I verify that running `pro api u.pro.services.disable.v1 --data '{"service": "realtime-kernel", "purge": true}'` `with sudo` exits `1`
    Then API errors field output is:
      """
      [
        {
          "code": "entitlement-not-disabled",
          "meta": {
            "reason": {
              "additional_info": null,
              "code": "disable-purge-not-supported",
              "title": "Real-time kernel does not support being disabled with --purge"
            }
          },
          "title": "failed to disable realtime-kernel"
        }
      ]
      """

    Examples:
      | release | machine_type |
      | jammy   | lxd-vm       |

  Scenario Outline: u.pro.services.disable.v1 with progress
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `apt-get update` with sudo
    And I attach `contract_token` with sudo
    # Basic disable
    And I run shell command `pro api u.pro.services.disable.v1 --show-progress --args service=esm-infra` with sudo
    Then stdout contains substring:
      """
      {"total_steps": 2, "done_steps": 0, "previous_step_message": null, "current_step_message": "Removing APT access to Ubuntu Pro: ESM Infra"}
      {"total_steps": 2, "done_steps": 1, "previous_step_message": "Removing APT access to Ubuntu Pro: ESM Infra", "current_step_message": "Updating package lists"}
      {"total_steps": 2, "done_steps": 2, "previous_step_message": "Updating package lists", "current_step_message": null}
      {"_schema_version": "v1", "data": {"attributes": {"disabled": ["esm-infra"]}, "meta": {"environment_vars": []}, "type": "DisableService"}, "errors": [], "result": "success"
      """
    # Disabling multiple services shows steps correctly
    When I run `pro enable ros-updates --assume-yes` with sudo
    When I run `pro api u.pro.services.disable.v1 --show-progress --args service=esm-apps` with sudo
    Then stdout contains substring:
      """
      {"total_steps": 6, "done_steps": 0, "previous_step_message": null, "current_step_message": "Removing APT access to ROS ESM All Updates"}
      {"total_steps": 6, "done_steps": 1, "previous_step_message": "Removing APT access to ROS ESM All Updates", "current_step_message": "Updating package lists"}
      {"total_steps": 6, "done_steps": 2, "previous_step_message": "Updating package lists", "current_step_message": "Removing APT access to ROS ESM Security Updates"}
      {"total_steps": 6, "done_steps": 3, "previous_step_message": "Removing APT access to ROS ESM Security Updates", "current_step_message": "Updating package lists"}
      {"total_steps": 6, "done_steps": 4, "previous_step_message": "Updating package lists", "current_step_message": "Removing APT access to Ubuntu Pro: ESM Apps"}
      {"total_steps": 6, "done_steps": 5, "previous_step_message": "Removing APT access to Ubuntu Pro: ESM Apps", "current_step_message": "Updating package lists"}
      {"total_steps": 6, "done_steps": 6, "previous_step_message": "Updating package lists", "current_step_message": null}
      {"_schema_version": "v1", "data": {"attributes": {"disabled": ["esm-apps", "ros", "ros-updates"]}, "meta": {"environment_vars": []}, "type": "DisableService"}, "errors": [], "result": "success"
      """

    Examples:
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
