Feature: u.pro.services.enable

    Scenario Outline: u.pro.services.enable.v1 container services
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I apt update
        And I apt install `jq`

        # Requires attach
        When I verify that running `pro api u.pro.services.enable.v1 --args service=esm-infra` `with sudo` exits `1`
        When I run shell command `pro api u.pro.services.enable.v1 --args service=esm-infra | jq .errors[0]` with sudo
        Then I will see the following on stdout:
        """
        {
          "code": "unattached",
          "meta": {},
          "title": "This machine is not attached to an Ubuntu Pro subscription.\nSee https://ubuntu.com/pro"
        }
        """

        When I attach `contract_token` with sudo and options `--no-auto-enable`

        # Requires root
        When I verify that running `pro api u.pro.services.enable.v1 --args service=esm-infra` `as non-root` exits `1`
        When I run shell command `pro api u.pro.services.enable.v1 --args service=esm-infra | jq .errors[0]` as non-root
        Then I will see the following on stdout:
        """
        {
          "code": "nonroot-user",
          "meta": {},
          "title": "This command must be run as root (try using sudo)."
        }
        """
        
        # Basic enable
        When I run shell command `pro api u.pro.services.enable.v1 --args service=esm-infra | jq .data.attributes` with sudo
        Then I will see the following on stdout:
        """
        {
          "disabled": [],
          "enabled": [
            "esm-infra"
          ],
          "messages": [],
          "reboot_required": false
        }
        """
        Then I verify that `esm-infra` is enabled
        # Enable already enabled service succeeds
        When I run shell command `pro api u.pro.services.enable.v1 --args service=esm-infra | jq .data.attributes` with sudo
        Then I will see the following on stdout:
        """
        {
          "disabled": [],
          "enabled": [],
          "messages": [],
          "reboot_required": false
        }
        """
        # enables required services
        When I run shell command `pro api u.pro.services.enable.v1 --args service=ros | jq .data.attributes` with sudo
        Then I will see the following on stdout:
        """
        {
          "disabled": [],
          "enabled": [
            "esm-apps",
            "ros"
          ],
          "messages": [],
          "reboot_required": false
        }
        """
        # Access only works and post enable messages work
        When I run shell command `pro api u.pro.services.enable.v1 --data \"{\\\"service\\\": \\\"cis\\\", \\\"access_only\\\": true}\" | jq .data.attributes` with sudo
        Then I will see the following on stdout:
        """
        {
          "disabled": [],
          "enabled": [
            "cis"
          ],
          "messages": [
            "Visit https://ubuntu.com/security/cis to learn how to use CIS"
          ],
          "reboot_required": false
        }
        """
        When I run `apt-cache policy usg-common` as non-root
        Then stdout contains substring:
        """
        Installed: (none)
        """
        # Access only on service that doesn't support it fails
        When I verify that running `pro api u.pro.services.enable.v1 --data '{"service": "ros-updates", "access_only": true}'` `with sudo` exits `1`
        When I run shell command `pro api u.pro.services.enable.v1 --data \"{\\\"service\\\": \\\"ros-updates\\\", \\\"access_only\\\": true}\" | jq .errors[0]` with sudo
        Then I will see the following on stdout:
        """
        {
          "code": "entitlement-not-enabled",
          "meta": {
            "reason": {
              "code": "enable-access-only-not-supported",
              "title": "ROS ESM All Updates does not support being enabled with --access-only"
            }
          },
          "title": "failed to enable ros-updates"
        }
        """
        Examples:
           | release | machine_type  |
           | xenial  | lxd-container |
           | bionic  | lxd-container |

    Scenario Outline: u.pro.services.enable.v1 landscape
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I apt update
        And I apt install `jq`
        And I attach `contract_token` with sudo and options `--no-auto-enable`

        When I verify that running `pro api u.pro.services.enable.v1 --args service=landscape` `with sudo` exits `1`
        And I run shell command `pro api u.pro.services.enable.v1 --args service=landscape | jq .errors[0]` with sudo
        Then I will see the following on stdout:
        """
        {
          "code": "not-supported",
          "meta": {},
          "title": "The operation is not supported"
        }
        """
        Examples:
           | release | machine_type  |
           | mantic  | lxd-container |

    Scenario Outline: u.pro.services.enable.v1 vm services
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I apt update
        And I apt install `jq`
        And I attach `contract_token` with sudo and options `--no-auto-enable`
        
        # Basic enable
        And I run shell command `pro api u.pro.services.enable.v1 --args service=livepatch | jq .data.attributes` with sudo
        Then I will see the following on stdout:
        """
        {
          "disabled": [],
          "enabled": [
            "livepatch"
          ],
          "messages": [],
          "reboot_required": false
        }
        """
        # disables incompatible services and variant works
        When I run shell command `pro api u.pro.services.enable.v1 --data \"{\\\"service\\\": \\\"realtime-kernel\\\", \\\"variant\\\": \\\"intel-iotg\\\"}\" | jq .data.attributes` with sudo
        Then I will see the following on stdout:
        """
        {
          "disabled": [
            "livepatch"
          ],
          "enabled": [
            "realtime-kernel"
          ],
          "messages": [],
          "reboot_required": true
        }
        """
        When I run shell command `pro api u.pro.status.enabled_services.v1 | jq ".data.attributes.enabled_services | select(.name==\"realtime-kernel\")" ` with sudo
        Then I will see the following on stdout:
        """
        [
          {
            "name": "realtime-kernel",
            "variant_enabled": true,
            "variant_name": "intel-iotg"
          }
        ]
        """
        Examples:
           | release | machine_type |
           | jammy   | lxd-vm       |

    Scenario Outline: u.pro.services.enable.v1 with progress
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I run `apt-get update` with sudo
        And I apt install `jq`
        And I attach `contract_token` with sudo and options `--no-auto-enable`
        
        # Basic enable
        And I run shell command `pro api u.pro.services.enable.v1 --show-progress --args service=esm-infra` with sudo
        Then I will see the following on stdout:
        """
        {}
        """
        # Enabling multiple services shows steps correctly 
        When I run shell command `pro api u.pro.services.enable.v1 --show-progress --args service=ros` with sudo
        Then I will see the following on stdout:
        """
        {}
        """
