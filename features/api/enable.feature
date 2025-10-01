Feature: u.pro.services.enable

  @arm64
  Scenario Outline: u.pro.services.enable.v1 container services
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I apt update
    # Requires attach
    When I verify that running `pro api u.pro.services.enable.v1 --args service=esm-infra` `with sudo` exits `1`
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
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    # Requires root
    When I verify that running `pro api u.pro.services.enable.v1 --args service=esm-infra` `as non-root` exits `1`
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
    When I verify that running `pro api u.pro.services.enable.v1 --args service=invalid` `with sudo` exits `1`
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
    # Basic enable
    When I run `pro api u.pro.services.enable.v1 --args service=esm-infra` with sudo
    Then API data field output is:
      """
      {
        "attributes": {
          "disabled": [],
          "enabled": [
            "esm-infra"
          ],
          "messages": [],
          "reboot_required": false
        },
        "meta": {
          "environment_vars": []
        },
        "type": "EnableService"
      }
      """
    Then I verify that `esm-infra` is enabled
    # Enable already enabled service succeeds
    When I run `pro api u.pro.services.enable.v1 --args service=esm-infra` with sudo
    Then API data field output is:
      """
      {
        "attributes": {
          "disabled": [],
          "enabled": [],
          "messages": [],
          "reboot_required": false
        },
        "meta": {
          "environment_vars": []
        },
        "type": "EnableService"
      }
      """
    # enables required services
    When I run `pro api u.pro.services.enable.v1 --args service=ros` with sudo
    Then API data field output is:
      """
      {
        "attributes": {
          "disabled": [],
          "enabled": [
            "esm-apps",
            "ros"
          ],
          "messages": [],
          "reboot_required": false
        },
        "meta": {
          "environment_vars": []
        },
        "type": "EnableService"
      }
      """
    # Access only works and post enable messages work
    When I run `pro api u.pro.services.enable.v1 --data '{"service": "cis", "access_only": true}'` with sudo
    Then API data field output is:
      """
      {
        "attributes": {
          "disabled": [],
          "enabled": [
            "cis"
          ],
          "messages": [
            "Visit https://ubuntu.com/security/cis to learn how to use CIS"
          ],
          "reboot_required": false
        },
        "meta": {
          "environment_vars": []
        },
        "type": "EnableService"
      }
      """
    When I run `apt-cache policy usg-common` as non-root
    Then stdout contains substring:
      """
      Installed: (none)
      """
    # Access only on service that doesn't support it fails
    When I verify that running `pro api u.pro.services.enable.v1 --data '{"service": "ros-updates", "access_only": true}'` `with sudo` exits `1`
    Then API errors field output is:
      """
      [
        {
          "code": "entitlement-not-enabled",
          "meta": {
            "reason": {
              "additional_info": null,
              "code": "enable-access-only-not-supported",
              "title": "ROS ESM All Updates does not support being enabled with --access-only"
            }
          },
          "title": "failed to enable ros-updates"
        }
      ]
      """

    Examples:
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |

  Scenario Outline: u.pro.services.enable.v1 landscape
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I apt update
    And I attach `contract_token` with sudo and options `--no-auto-enable`
    When I verify that running `pro api u.pro.services.enable.v1 --args service=landscape` `with sudo` exits `1`
    Then API errors field output is:
      """
      [
        {
          "code": "not-supported",
          "meta": {},
          "title": "The operation is not supported"
        }
      ]
      """

    Examples:
      | release  | machine_type  |
      | noble    | lxd-container |
      | plucky   | lxd-container |
      | questing | lxd-container |

  Scenario Outline: u.pro.services.enable.v1 vm services
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I apt update
    And I attach `contract_token` with sudo and options `--no-auto-enable`
    # Basic enable
    And I run `pro api u.pro.services.enable.v1 --args service=livepatch` with sudo
    Then API data field output is:
      """
      {
        "attributes": {
          "disabled": [],
          "enabled": [
            "livepatch"
          ],
          "messages": [],
          "reboot_required": false
        },
        "meta": {
          "environment_vars": []
        },
        "type": "EnableService"
      }
      """
    # disables incompatible services and variant works
    When I run `pro api u.pro.services.enable.v1 --data '{"service": "realtime-kernel", "variant": "intel-iotg"}'` with sudo
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "disabled": [
            "livepatch"
          ],
          "enabled": [
            "realtime-kernel"
          ],
          "messages": [],
          "reboot_required": true
        },
        "meta": {
          "environment_vars": []
        },
        "type": "EnableService"
      }
      """
    When I run `pro api u.pro.status.enabled_services.v1` with sudo
    Then API data field output matches regexp:
      """
      \s*{
      \s*  "name": "realtime-kernel",
      \s*  "variant_enabled": true,
      \s*  "variant_name": "intel-iotg"
      \s*}
      """

    Examples:
      | release | machine_type |
      | jammy   | lxd-vm       |

  Scenario Outline: u.pro.services.enable.v1 with progress
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `apt-get update` with sudo
    And I attach `contract_token` with sudo and options `--no-auto-enable`
    # Basic enable
    And I run shell command `pro api u.pro.services.enable.v1 --show-progress --args service=esm-infra` with sudo
    Then stdout contains substring:
      """
      {"total_steps": 2, "done_steps": 0, "previous_step_message": null, "current_step_message": "Configuring APT access to Ubuntu Pro: ESM Infra"}
      {"total_steps": 2, "done_steps": 1, "previous_step_message": "Configuring APT access to Ubuntu Pro: ESM Infra", "current_step_message": "Updating Ubuntu Pro: ESM Infra package lists"}
      {"total_steps": 2, "done_steps": 2, "previous_step_message": "Updating Ubuntu Pro: ESM Infra package lists", "current_step_message": null}
      {"_schema_version": "v1", "data": {"attributes": {"disabled": [], "enabled": ["esm-infra"], "messages": [], "reboot_required": false}, "meta": {"environment_vars": []}, "type": "EnableService"}, "errors": [], "result": "success"
      """
    # Enabling multiple services shows steps correctly
    When I run shell command `pro api u.pro.services.enable.v1 --show-progress --args service=ros-updates` with sudo
    Then stdout contains substring:
      """
      {"total_steps": 6, "done_steps": 0, "previous_step_message": null, "current_step_message": "Configuring APT access to Ubuntu Pro: ESM Apps"}
      {"total_steps": 6, "done_steps": 1, "previous_step_message": "Configuring APT access to Ubuntu Pro: ESM Apps", "current_step_message": "Updating Ubuntu Pro: ESM Apps package lists"}
      {"total_steps": 6, "done_steps": 2, "previous_step_message": "Updating Ubuntu Pro: ESM Apps package lists", "current_step_message": "Configuring APT access to ROS ESM Security Updates"}
      {"total_steps": 6, "done_steps": 3, "previous_step_message": "Configuring APT access to ROS ESM Security Updates", "current_step_message": "Updating ROS ESM Security Updates package lists"}
      {"total_steps": 6, "done_steps": 4, "previous_step_message": "Updating ROS ESM Security Updates package lists", "current_step_message": "Configuring APT access to ROS ESM All Updates"}
      {"total_steps": 6, "done_steps": 5, "previous_step_message": "Configuring APT access to ROS ESM All Updates", "current_step_message": "Updating ROS ESM All Updates package lists"}
      {"total_steps": 6, "done_steps": 6, "previous_step_message": "Updating ROS ESM All Updates package lists", "current_step_message": null}
      {"_schema_version": "v1", "data": {"attributes": {"disabled": [], "enabled": ["esm-apps", "ros", "ros-updates"], "messages": [], "reboot_required": false}, "meta": {"environment_vars": []}, "type": "EnableService"}, "errors": [], "result": "success"
      """

    Examples:
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |

  Scenario Outline: u.pro.services.enable.v1 vm services with progress
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I apt update
    And I attach `contract_token` with sudo and options `--no-auto-enable`
    And I run `pro api u.pro.services.enable.v1 --args service=livepatch --show-progress` with sudo
    Then stdout contains substring:
      """
      {"total_steps": 2, "done_steps": 0, "previous_step_message": null, "current_step_message": "Installing Livepatch"}
      {"total_steps": 2, "done_steps": 1, "previous_step_message": "Installing Livepatch", "current_step_message": "Setting up Livepatch"}
      {"total_steps": 2, "done_steps": 2, "previous_step_message": "Setting up Livepatch", "current_step_message": null}
      {"_schema_version": "v1", "data": {"attributes": {"disabled": [], "enabled": ["livepatch"], "messages": [], "reboot_required": false}, "meta": {"environment_vars": []}, "type": "EnableService"}, "errors": [], "result": "success"
      """
    # disables incompatible services and variant works
    When I run `pro api u.pro.services.enable.v1 --show-progress --data '{"service": "realtime-kernel", "variant": "intel-iotg"}'` with sudo
    Then stdout contains substring:
      """
      {"total_steps": 4, "done_steps": 0, "previous_step_message": null, "current_step_message": "Executing `/snap/bin/canonical-livepatch disable`"}
      {"total_steps": 4, "done_steps": 1, "previous_step_message": "Executing `/snap/bin/canonical-livepatch disable`", "current_step_message": "Configuring APT access to Real-time Intel IOTG Kernel"}
      {"total_steps": 4, "done_steps": 2, "previous_step_message": "Configuring APT access to Real-time Intel IOTG Kernel", "current_step_message": "Updating Real-time Intel IOTG Kernel package lists"}
      {"total_steps": 4, "done_steps": 3, "previous_step_message": "Updating Real-time Intel IOTG Kernel package lists", "current_step_message": "Installing Real-time Intel IOTG Kernel packages"}
      {"total_steps": 4, "done_steps": 4, "previous_step_message": "Installing Real-time Intel IOTG Kernel packages", "current_step_message": null}
      {"_schema_version": "v1", "data": {"attributes": {"disabled": ["livepatch"], "enabled": ["realtime-kernel"], "messages": [], "reboot_required": true}, "meta": {"environment_vars": []}, "type": "EnableService"}, "errors": [], "result": "success"
      """
    When I run `pro api u.pro.status.enabled_services.v1` with sudo
    Then API data field output matches regexp:
      """
      \s*{
      \s*  "name": "realtime-kernel",
      \s*  "variant_enabled": true,
      \s*  "variant_name": "intel-iotg"
      \s*}
      """

    Examples:
      | release | machine_type |
      | jammy   | lxd-vm       |
