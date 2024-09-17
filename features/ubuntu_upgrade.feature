@uses.config.contract_token
Feature: Upgrade between releases when uaclient is attached

  @slow @upgrade
  Scenario Outline: Attached upgrade
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I run `<before_cmd>` with sudo
    # Local PPAs are prepared and served only when testing with local debs
    And I prepare the local PPAs to upgrade from `<release>` to `<next_release>`
    And I run `DEBIAN_FRONTEND=noninteractive apt-get dist-upgrade --assume-yes` with sudo
    # Some packages upgrade may require a reboot
    And I reboot the machine
    And I create the file `/etc/update-manager/release-upgrades.d/ua-test.cfg` with the following
      """
      [Sources]
      AllowThirdParty=yes
      """
    And I run `sed -i 's/Prompt=lts/Prompt=<prompt>/' /etc/update-manager/release-upgrades` with sudo
    And I run `do-release-upgrade <devel_release> --frontend DistUpgradeViewNonInteractive` `with sudo` and stdin `y\n`
    And I reboot the machine
    And I run `lsb_release -cs` as non-root
    Then I will see the following on stdout:
      """
      <next_release>
      """
    And I verify that running `egrep "<release>|disabled" /etc/apt/sources.list.d/*` `as non-root` exits `2`
    And I will see the following on stdout:
      """
      """
    When I run `pro refresh` with sudo
    And I run `pro status --all` with sudo
    Then stdout matches regexp:
      """
      <service1> +yes +<service1_status>
      """
    Then stdout matches regexp:
      """
      <service2> +yes +<service2_status>
      """
    When I run `pro detach --assume-yes` with sudo
    Then stdout matches regexp:
      """
      This machine is now detached.
      """

    Examples: ubuntu release
      | release | machine_type  | next_release | prompt | devel_release | service1  | service1_status | service2 | service2_status | before_cmd     |
      | xenial  | lxd-container | bionic       | lts    |               | esm-infra | enabled         | esm-apps | enabled         | true           |
      | bionic  | lxd-container | focal        | lts    |               | esm-infra | enabled         | esm-apps | enabled         | true           |
      | bionic  | lxd-container | focal        | lts    |               | usg       | enabled         | usg      | enabled         | pro enable cis |
      | focal   | lxd-container | jammy        | lts    |               | esm-infra | enabled         | esm-apps | enabled         | true           |

  # This test is unideal.
  # do-release-upgrade started disabling proposed on upgrade, which prevents us from testing the upgrade from
  # jammy-proposed to noble-proposed of pro-client. Ideally we'd have a way to leave -proposed enabled during the upgrade.
  # Since there is no feature of do-release-upgrade to leave -proposed enabled, this test does the release upgrade,
  # then re-enables proposed and then installs pro-client from -proposed.
  # This is unideal, because the jammy-proposed pro-client will still be installed until the extra steps to re-enable
  # -proposed and upgrade from there. The jammy-proposed release-upgrades.d script will run, and the jammy-proposed
  # apparmor profiles will remain installed. The apparmor profiles are particularly problematic, because the noble
  # profiles require extra rules. That is why this test needs to mask the apparmored systemd units during the upgrade of
  # pro-client after the release upgrade.
  @slow @upgrade
  Scenario Outline: Attached upgrade jammy to noble
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    # Local PPAs are prepared and served only when testing with local debs
    And I prepare the local PPAs to upgrade from `<release>` to `<next_release>`
    And I run `DEBIAN_FRONTEND=noninteractive apt-get dist-upgrade --assume-yes` with sudo
    # Some packages upgrade may require a reboot
    And I reboot the machine
    And I create the file `/etc/update-manager/release-upgrades.d/ua-test.cfg` with the following
      """
      [Sources]
      AllowThirdParty=yes
      """
    And I run `sed -i 's/Prompt=lts/Prompt=<prompt>/' /etc/update-manager/release-upgrades` with sudo
    And I run `do-release-upgrade <devel_release> --frontend DistUpgradeViewNonInteractive` `with sudo` and stdin `y\n`
    When I run `systemctl mask apt-news.service` with sudo
    When I run `systemctl mask esm-cache.service` with sudo
    And I update the series in the machine test metadata to `<next_release>`
    And I install ubuntu-advantage-tools
    When I run `systemctl unmask esm-cache.service` with sudo
    When I run `systemctl unmask apt-news.service` with sudo
    And I reboot the machine
    And I run `lsb_release -cs` as non-root
    Then I will see the following on stdout:
      """
      <next_release>
      """
    And I verify that running `egrep "<release>|disabled" /etc/apt/sources.list.d/*` `as non-root` exits `2`
    And I will see the following on stdout:
      """
      """
    When I run `pro refresh` with sudo
    And I run `pro status --all` with sudo
    Then stdout matches regexp:
      """
      <service1> +yes +<service1_status>
      """
    Then stdout matches regexp:
      """
      <service2> +yes +<service2_status>
      """
    When I run `pro detach --assume-yes` with sudo
    Then stdout matches regexp:
      """
      This machine is now detached.
      """

    Examples: ubuntu release
      | release | machine_type  | next_release | prompt | devel_release   | service1  | service1_status | service2 | service2_status |
      | jammy   | lxd-container | noble        | lts    | --devel-release | esm-infra | enabled         | esm-apps | enabled         |

  @slow @upgrade
  Scenario Outline: Attached FIPS upgrade across LTS releases
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I apt install `lsof`
    And I run `pro disable livepatch` with sudo
    And I run `pro enable <fips-service> --assume-yes` with sudo
    Then stdout contains substring:
      """
      One moment, checking your subscription first
      Configuring APT access to <fips-name>
      Updating <fips-name> package lists
      Updating standard Ubuntu package lists
      Installing <fips-name> packages
      <fips-name> enabled
      A reboot is required to complete install.
      """
    When I run `pro status --all` with sudo
    Then I verify that `<fips-service>` is enabled
    And I ensure apt update runs without errors
    When I reboot the machine
    And I run `uname -r` as non-root
    Then stdout matches regexp:
      """
      fips
      """
    When I run `cat /proc/sys/crypto/fips_enabled` with sudo
    Then I will see the following on stdout:
      """
      1
      """
    # Local PPAs are prepared and served only when testing with local debs
    When I prepare the local PPAs to upgrade from `<release>` to `<next_release>`
    And I run `DEBIAN_FRONTEND=noninteractive apt-get dist-upgrade -y --allow-downgrades` with sudo
    # A package may need a reboot after running dist-upgrade
    And I reboot the machine
    And I create the file `/etc/update-manager/release-upgrades.d/ua-test.cfg` with the following
      """
      [Sources]
      AllowThirdParty=yes
      """
    Then I verify that running `do-release-upgrade --frontend DistUpgradeViewNonInteractive` `with sudo` exits `0`
    When I reboot the machine
    And I run `lsb_release -cs` as non-root
    Then I will see the following on stdout:
      """
      <next_release>
      """
    When I verify that running `egrep "disabled" /etc/apt/sources.list.d/<source-file>.list` `as non-root` exits `1`
    Then I will see the following on stdout:
      """
      """
    When I run `pro status --all` with sudo
    Then I verify that `<fips-service>` is enabled
    When I run `uname -r` as non-root
    Then stdout matches regexp:
      """
      fips
      """
    When I run `cat /proc/sys/crypto/fips_enabled` with sudo
    Then I will see the following on stdout:
      """
      1
      """

    Examples: ubuntu release
      | release | machine_type | next_release | fips-service | fips-name    | source-file         |
      | xenial  | lxd-vm       | bionic       | fips         | FIPS         | ubuntu-fips         |
      | xenial  | lxd-vm       | bionic       | fips-updates | FIPS Updates | ubuntu-fips-updates |

  @slow @upgrade
  Scenario Outline: Check onlySeries on reboot after upgrade
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/tmp/response-overlay.json` with the following:
      """
      {
          "https://contracts.canonical.com/v1/context/machines/token": [
          {
            "code": 200,
            "response": {
              "machineTokenInfo": {
                "accountInfo": {
                  "name": "testName",
                  "id": "testAccID"
                },
                "contractInfo": {
                  "id": "testCID",
                  "name": "testName",
                  "resourceEntitlements": [
                    {
                      "type": "support",
                      "affordances": {
                        "onlySeries": "<onlyseries>"
                      }
                    }
                  ]
                },
                "machineId": "testMID"
              }
            }
        }],
        "https://contracts.canonical.com/v1/contracts/testCID/context/machines/testMID": [
          {
            "code": 200,
            "response": {
              "activityToken": "test-activity-token",
              "activityID": "test-activity-id",
              "activityPingInterval": 123456789
            }
          }],
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
        serviceclient_url_responses: "/tmp/response-overlay.json"
      """
    When I attach `contract_token` with sudo
    Then the machine is attached
    When I prepare the local PPAs to upgrade from `<release>` to `<next_release>`
    And I run `DEBIAN_FRONTEND=noninteractive apt-get dist-upgrade --assume-yes` with sudo
    # Some packages upgrade may require a reboot
    And I reboot the machine
    And I create the file `/etc/update-manager/release-upgrades.d/ua-test.cfg` with the following
      """
      [Sources]
      AllowThirdParty=yes
      """
    And I run `sed -i 's/Prompt=lts/Prompt=<prompt>/' /etc/update-manager/release-upgrades` with sudo
    Then I verify that running `do-release-upgrade --frontend DistUpgradeViewNonInteractive` `with sudo` exits `0`
    When I reboot the machine
    And I run `lsb_release -cs` as non-root
    Then I will see the following on stdout:
      """
      <next_release>
      """
    And the machine is unattached

    Examples: ubuntu release
      | release | machine_type  | next_release | onlyseries |
      | xenial  | lxd-container | bionic       | xenial     |
      | bionic  | lxd-container | focal        | bionic     |
      | focal   | lxd-container | jammy        | focal      |
