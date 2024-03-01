Feature: Creating golden images based on Cloud Ubuntu Pro instances

  Scenario Outline: Create a Pro fips-updates image and launch
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
      """
      contract_url: 'https://contracts.canonical.com'
      data_dir: /var/lib/ubuntu-advantage
      log_level: debug
      log_file: /var/log/ubuntu-advantage.log
      """
    When I run `pro auto-attach` with sudo
    Then the machine is attached
    When I apt install `jq`
    When I save the `activityInfo.activityToken` value from the contract
    When I save the `activityInfo.activityID` value from the contract
    When I run `pro enable fips-updates --assume-yes` with sudo
    And I run `pro status --format yaml` with sudo
    Then stdout matches regexp:
      """
      \s*name: fips-updates
      \s*status: enabled
      """
    When I reboot the machine
    When I take a snapshot of the machine
    When I reboot the machine
    When I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
    Then I verify that `activityInfo.activityToken` value has been updated on the contract
    Then I verify that `activityInfo.activityID` value has not been updated on the contract
    When I launch a `<release>` `<machine_type>` machine named `clone` from the snapshot of `system-under-test`
    # The clone will run auto-attach on boot
    When I run `pro status --wait` `with sudo` on the `clone` machine
    Then the machine is attached
    When I run `python3 /usr/lib/ubuntu-advantage/timer.py` `with sudo` on the `clone` machine
    Then I verify that `activityInfo.activityToken` value has been updated on the contract on the `clone` machine
    Then I verify that `activityInfo.activityID` value has been updated on the contract on the `clone` machine
    When I run `pro status --format yaml` `with sudo` on the `clone` machine
    Then stdout matches regexp:
      """
      \s*name: fips-updates
      \s*status: enabled
      """
    When I reboot the `clone` machine
    When I run `pro status --format yaml` `with sudo` on the `clone` machine
    Then stdout matches regexp:
      """
      \s*name: fips-updates
      \s*status: enabled
      """

    Examples: ubuntu release
      | release | machine_type |
      | bionic  | aws.pro      |
      | bionic  | gcp.pro      |
      | focal   | aws.pro      |
      | focal   | gcp.pro      |
