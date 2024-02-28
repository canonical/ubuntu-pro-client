@uses.config.contract_token
Feature: Enable anbox on Ubuntu

  Scenario Outline: Enable Anbox cloud service in a container
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    Then I verify that `anbox-cloud` is disabled
    Then I verify that running `pro enable anbox-cloud` `as non-root` exits `1`
    And I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    When I verify that running `pro enable anbox-cloud` `with sudo` exits `1`
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      It is only possible to enable Anbox Cloud on a container using
      the --access-only flag.
      """
    When I run `pro enable anbox-cloud --access-only` with sudo
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Updating Anbox Cloud package lists
      Anbox Cloud access enabled
      """
    And I verify that `anbox-cloud` is enabled
    When I run `apt-cache policy` with sudo
    Then apt-cache policy for the following url has priority `500`
      """
      https://archive.anbox-cloud.io/stable <release>/main amd64 Packages
      """
    When I run `pro disable anbox-cloud` with sudo
    Then I verify that `anbox-cloud` is disabled

    Examples: ubuntu release
      | release | machine_type  |
      | jammy   | lxd-container |

  Scenario Outline: Enable Anbox cloud service in an unsupported release
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    And I verify that running `pro enable anbox-cloud` `with sudo` exits `1`
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Anbox Cloud is not available for Ubuntu 16.04 LTS (Xenial Xerus).
      """

    Examples: ubuntu release
      | release | machine_type |
      | xenial  | lxd-vm       |

  Scenario Outline: Enable Anbox cloud service in a VM
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    And I run `snap remove lxd` with sudo
    And I run `pro enable anbox-cloud --access-only --assume-yes` with sudo
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Updating Anbox Cloud package lists
      Anbox Cloud access enabled
      """
    And I verify that `anbox-cloud` is enabled
    When I run `apt-cache policy` with sudo
    Then apt-cache policy for the following url has priority `500`
      """
      https://archive.anbox-cloud.io/stable <release>/main amd64 Packages
      """
    And I check that snap `amc` is not installed
    And I check that snap `lxd` is not installed
    And I check that snap `anbox-cloud-appliance` is not installed
    And I verify that files exist matching `/var/lib/ubuntu-advantage/private/anbox-cloud-credentials`
    When I run `cat /var/lib/ubuntu-advantage/private/anbox-cloud-credentials` with sudo
    Then stdout is a json matching the `anbox_cloud_credentials` schema
    When I run `pro disable anbox-cloud` with sudo
    Then I verify that `anbox-cloud` is disabled
    And I verify that no files exist matching `/var/lib/ubuntu-advantage/private/anbox-cloud-credentials`
    When I run `pro enable anbox-cloud --assume-yes` with sudo
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Installing required snaps
      Installing required snap: amc
      Installing required snap: anbox-cloud-appliance
      Installing required snap: lxd
      Updating Anbox Cloud package lists
      Anbox Cloud enabled
      To finish setting up the Anbox Cloud Appliance, run:

      $ sudo anbox-cloud-appliance init

      You can accept the default answers if you do not have any specific
      configuration changes.
      For more information, see https://anbox-cloud.io/docs/tut/installing-appliance#initialise
      """
    Then I verify that `anbox-cloud` is enabled
    When I run `apt-cache policy` with sudo
    Then apt-cache policy for the following url has priority `500`
      """
      https://archive.anbox-cloud.io/stable <release>/main amd64 Packages
      """
    And I check that snap `amc` is installed
    And I check that snap `lxd` is installed
    And I check that snap `anbox-cloud-appliance` is installed
    And I verify that files exist matching `/var/lib/ubuntu-advantage/private/anbox-cloud-credentials`
    When I run `cat /var/lib/ubuntu-advantage/private/anbox-cloud-credentials` with sudo
    Then stdout is a json matching the `anbox_cloud_credentials` schema
    When I run `pro disable anbox-cloud` with sudo
    Then I verify that `anbox-cloud` is disabled
    And I verify that no files exist matching `/var/lib/ubuntu-advantage/private/anbox-cloud-credentials`

    Examples: ubuntu release
      | release | machine_type |
      | jammy   | lxd-vm       |
