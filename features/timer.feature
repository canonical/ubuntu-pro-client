@uses.config.contract_token
Feature: Timer for regular background jobs while attached

  # earlies, latest lts, devel
  @arm64
  Scenario Outline: Timer is stopped when detached, started when attached
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    Then I verify the `ua-timer` systemd timer is disabled
    When I attach `contract_token` with sudo
    # 6 hour timer with 1 hour randomized delay -> potentially 7 hours
    Then I verify the `ua-timer` systemd timer is scheduled to run within `420` minutes
    When I run `pro detach --assume-yes` with sudo
    Then I verify the `ua-timer` systemd timer is disabled

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |
      | plucky  | lxd-container |

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
      | focal   | lxd-container |
      | focal   | wsl           |
      | jammy   | lxd-container |
      | noble   | lxd-container |
      | plucky  | lxd-container |

  Scenario Outline: Run timer script to validate machine activity endpoint
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
