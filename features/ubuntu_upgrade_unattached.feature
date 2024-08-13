Feature: Upgrade between releases when uaclient is unattached

  @slow @upgrade @uses.config.contract_token
  Scenario Outline: Unattached upgrade
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    # Local PPAs are prepared and served only when testing with local debs
    When I prepare the local PPAs to upgrade from `<release>` to `<next_release>`
    # in case this still exists
    And I delete the file `/var/lib/ubuntu-advantage/apt-esm/etc/apt/sources.list.d/ubuntu-esm-infra.list`
    And I apt update
    And I run `sleep 30` as non-root
    And I run shell command `cat /var/lib/ubuntu-advantage/apt-esm/etc/apt/sources.list.d/ubuntu-esm-infra.sources || true` with sudo
    Then if `<release>` in `xenial or bionic` and stdout matches regexp:
      """
      Types: deb
      URIs: https://esm.ubuntu.com/infra/ubuntu
      Suites: <release>-infra-security <release>-infra-updates
      Components: main
      Signed-By: /usr/share/keyrings/ubuntu-pro-esm-infra.gpg
      """
    When I apt dist-upgrade
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
    And I verify that the folder `/var/lib/ubuntu-advantage/apt-esm` does not exist
    When I apt update
    And I run shell command `cat /var/lib/ubuntu-advantage/apt-esm/etc/apt/sources.list.d/ubuntu-esm-apps.sources || true` with sudo
    Then if `<next_release>` not in `noble` and stdout matches regexp:
      """
      Types: deb
      URIs: https://esm.ubuntu.com/apps/ubuntu
      Suites: <next_release>-apps-security <next_release>-apps-updates
      Components: main
      Signed-By: /usr/share/keyrings/ubuntu-pro-esm-apps.gpg
      """
    When I attach `contract_token` with sudo
    And I run `pro status --all` with sudo
    Then stdout matches regexp:
      """
      esm-infra +yes +<service_status>
      """

    Examples: ubuntu release
      | release | machine_type  | next_release | prompt | devel_release | service_status |
      | xenial  | lxd-container | bionic       | lts    |               | enabled        |
      | bionic  | lxd-container | focal        | lts    |               | enabled        |
      | focal   | lxd-container | jammy        | lts    |               | enabled        |

# No path from Jammy to Noble until .1 is there
# | jammy   | lxd-container | noble        | lts    |                 | enabled        |
