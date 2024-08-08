@uses.config.contract_token
Feature: Command behaviour when attached to an Ubuntu Pro subscription

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
      | release | machine_type  |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | xenial  | lxd-container |
      | jammy   | lxd-container |
      | mantic  | lxd-container |
      | noble   | lxd-container |

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

  Scenario Outline: Attached enable when reboot required
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I run `pro disable esm-infra` with sudo
    And I run `touch /var/run/reboot-required` with sudo
    And I run `touch /var/run/reboot-required.pkgs` with sudo
    And I run `pro enable esm-infra` with sudo
    Then stdout matches regexp:
      """
      Updating Ubuntu Pro: ESM Infra package lists
      Ubuntu Pro: ESM Infra enabled
      """
    And stdout does not match regexp:
      """
      A reboot is required to complete install.
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |

  Scenario Outline: Help command on an attached machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I run `pro help esm-infra` with sudo
    Then I will see the following on stdout:
      """
      Name:
      esm-infra

      Entitled:
      yes

      Status:
      <infra-status>

      Help:
      Expanded Security Maintenance for Infrastructure provides access to a private
      PPA which includes available high and critical CVE fixes for Ubuntu LTS
      packages in the Ubuntu Main repository between the end of the standard Ubuntu
      LTS security maintenance and its end of life. It is enabled by default with
      Ubuntu Pro. You can find out more about the service at
      https://ubuntu.com/security/esm
      """
    When I run `pro help esm-infra --format json` with sudo
    Then I will see the following on stdout:
      """
      {"name": "esm-infra", "entitled": "yes", "status": "<infra-status>", "help": "Expanded Security Maintenance for Infrastructure provides access to a private\nPPA which includes available high and critical CVE fixes for Ubuntu LTS\npackages in the Ubuntu Main repository between the end of the standard Ubuntu\nLTS security maintenance and its end of life. It is enabled by default with\nUbuntu Pro. You can find out more about the service at\nhttps://ubuntu.com/security/esm"}
      """
    And I verify that running `pro help invalid-service` `with sudo` exits `1`
    And I will see the following on stderr:
      """
      No help available for 'invalid-service'
      """

    Examples: ubuntu release
      | release | machine_type  | infra-status |
      | bionic  | lxd-container | enabled      |
      | xenial  | lxd-container | enabled      |
      | mantic  | lxd-container | n/a          |

  Scenario Outline: Help command on an attached machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I run `pro help esm-infra` with sudo
    Then I will see the following on stdout:
      """
      Name:
      esm-infra

      Entitled:
      yes

      Status:
      enabled

      Help:
      Expanded Security Maintenance for Infrastructure provides access to a private
      PPA which includes available high and critical CVE fixes for Ubuntu LTS
      packages in the Ubuntu Main repository between the end of the standard Ubuntu
      LTS security maintenance and its end of life. It is enabled by default with
      Ubuntu Pro. You can find out more about the service at
      https://ubuntu.com/security/esm
      """
    When I run `pro help esm-infra --format json` with sudo
    Then I will see the following on stdout:
      """
      {"name": "esm-infra", "entitled": "yes", "status": "enabled", "help": "Expanded Security Maintenance for Infrastructure provides access to a private\nPPA which includes available high and critical CVE fixes for Ubuntu LTS\npackages in the Ubuntu Main repository between the end of the standard Ubuntu\nLTS security maintenance and its end of life. It is enabled by default with\nUbuntu Pro. You can find out more about the service at\nhttps://ubuntu.com/security/esm"}
      """
    And I verify that running `pro help invalid-service` `with sudo` exits `1`
    And I will see the following on stderr:
      """
      No help available for 'invalid-service'
      """

    Examples: ubuntu release
      | release | machine_type  |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |

  Scenario Outline: Run timer script on an attached machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `systemctl stop ua-timer.timer` with sudo
    And I attach `contract_token` with sudo
    Then I verify that running `pro config set update_messaging_timer=-2` `with sudo` exits `1`
    And stderr matches regexp:
      """
      Cannot set update_messaging_timer to -2: <value> for interval must be a positive integer.
      """
    When I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
    And I run `cat /var/lib/ubuntu-advantage/jobs-status.json` with sudo
    Then stdout matches regexp:
      """
      "update_messaging":
      """
    When I run `pro config show` with sudo
    Then stdout matches regexp:
      """
      update_messaging_timer  +21600
      """
    When I delete the file `/var/lib/ubuntu-advantage/jobs-status.json`
    And I run `pro config set update_messaging_timer=0` with sudo
    And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
    And I run `cat /var/lib/ubuntu-advantage/jobs-status.json` with sudo
    Then stdout matches regexp:
      """
      "update_messaging": null
      """
    When I delete the file `/var/lib/ubuntu-advantage/jobs-status.json`
    And I create the file `/var/lib/ubuntu-advantage/private/user-config.json` with the following:
      """
      { "metering_timer": 0 }
      """
    And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
    And I run `cat /var/lib/ubuntu-advantage/jobs-status.json` with sudo
    Then stdout matches regexp:
      """
      "metering": null
      """
    When I delete the file `/var/lib/ubuntu-advantage/jobs-status.json`
    And I create the file `/var/lib/ubuntu-advantage/private/user-config.json` with the following:
      """
      { "metering_timer": "notanumber", "update_messaging_timer": -10 }
      """
    And I run `systemctl start ua-timer.service` with sudo
    Then I verify that running `sh -c 'journalctl -u ua-timer.service | grep "Invalid value for update_messaging interval found in config."'` `with sudo` exits `0`
    And I verify that the timer interval for `update_messaging` is `21600`
    And I verify that the timer interval for `metering` is `14400`
    When I create the file `/var/lib/ubuntu-advantage/jobs-status.json` with the following:
      """
      {"metering": {"last_run": "2022-11-29T19:15:52.434906+00:00", "next_run": "2022-11-29T23:15:52.434906+00:00"}, "update_messaging": {"last_run": "2022-11-29T19:15:52.434906+00:00", "next_run": "2022-11-30T01:15:52.434906+00:00"}, "update_status": {"last_run": "2022-11-29T19:15:52.434906+00:00", "next_run": "2022-11-30T01:15:52.434906+00:00"}}
      """
    And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
    And I run `cat /var/lib/ubuntu-advantage/jobs-status.json` with sudo
    Then stdout does not match regexp:
      """
      "update_status"
      """
    And stdout matches regexp:
      """
      "metering"
      """
    And stdout matches regexp:
      """
      "update_messaging"
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | bionic  | wsl           |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | mantic  | lxd-container |
      | noble   | lxd-container |

  Scenario Outline: Run timer script to valid machine activity endpoint
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I apt update
    And I apt install `jq`
    And I save the `activityInfo.activityToken` value from the contract
    And I save the `activityInfo.activityID` value from the contract
    # normal metering call when activityId is set by attach response above, expect new
    # token and same id
    And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
    Then I verify that `activityInfo.activityToken` value has been updated on the contract
    And I verify that `activityInfo.activityID` value has not been updated on the contract
    When I restore the saved `activityInfo.activityToken` value on contract
    And I delete the file `/var/lib/ubuntu-advantage/jobs-status.json`
    # simulate "cloned" metering call where previously used activityToken is sent again,
    # expect new token and new id
    And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
    Then I verify that `activityInfo.activityToken` value has been updated on the contract
    And I verify that `activityInfo.activityID` value has been updated on the contract
    # We are keeping this test to guarantee that the activityPingInterval is also updated
    When I create the file `/var/lib/ubuntu-advantage/machine-token-overlay.json` with the following:
      """
      {
          "machineTokenInfo": {
              "contractInfo": {
                 "id": "testCID"
              },
              "machineId": "testMID"
          }
      }
      """
    And I create the file `/var/lib/ubuntu-advantage/response-overlay.json` with the following:
      """
      {
          "https://contracts.canonical.com/v1/contracts/testCID/machine-activity/testMID": [
          {
            "code": 200,
            "response": {
              "activityToken": "test-activity-token",
              "activityID": "test-activity-id",
              "activityPingInterval": 123456789
            }
          }]
      }
      """
    And I append the following on uaclient config:
      """
      features:
        machine_token_overlay: "/var/lib/ubuntu-advantage/machine-token-overlay.json"
        serviceclient_url_responses: "/var/lib/ubuntu-advantage/response-overlay.json"
      """
    When I delete the file `/var/lib/ubuntu-advantage/jobs-status.json`
    And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
    Then I verify that running `grep -q activityInfo /var/lib/ubuntu-advantage/private/machine-token.json` `with sudo` exits `0`
    And I verify that running `grep -q "\"activityToken\": \"test-activity-token\"" /var/lib/ubuntu-advantage/private/machine-token.json` `with sudo` exits `0`
    And I verify that running `grep -q "\"activityID\": \"test-activity-id\"" /var/lib/ubuntu-advantage/private/machine-token.json` `with sudo` exits `0`
    And I verify that running `grep -q "\"activityPingInterval\": 123456789" /var/lib/ubuntu-advantage/private/machine-token.json` `with sudo` exits `0`
    When I run `cat /var/lib/ubuntu-advantage/jobs-status.json` with sudo
    Then stdout matches regexp:
      """
      \"metering\"
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |

  Scenario Outline: Run timer script to valid machine activity endpoint
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I run `rm /var/lib/ubuntu-advantage/machine-token.json` with sudo
    Then the machine is unattached
    When I run `dpkg-reconfigure ubuntu-advantage-tools` with sudo
    Then I verify that files exist matching `/var/lib/ubuntu-advantage/machine-token.json`
    Then the machine is attached

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
