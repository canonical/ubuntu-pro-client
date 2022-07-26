Feature: Creating golden images based on Cloud Ubuntu Pro instances

    @series.lts
    @uses.config.machine_type.aws.pro
    @uses.config.machine_type.azure.pro
    @uses.config.machine_type.gcp.pro
    Scenario Outline: Create a Pro fips-updates image and launch
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        When I run `pro auto-attach` with sudo
        And I run `pro status --format yaml` with sudo
        Then stdout matches regexp:
        """
        attached: true
        """
        When I run `apt install -y jq` with sudo
        When I save the `activityInfo.activityID` value from the contract
        When I run `pro enable fips-updates --assume-yes` with sudo
        And I run `pro status --format yaml` with sudo
        Then stdout matches regexp:
        """
          name: fips-updates
          status: enabled
        """
        When I reboot the machine
        When I take a snapshot of the machine
        When I launch a `clone` machine from the snapshot
        # The clone will run auto-attach on boot
        When I run `pro status --wait` `with sudo` on the `clone` machine
        When I run `pro status --format yaml` `with sudo` on the `clone` machine
        Then stdout matches regexp:
        """
        attached: true
        """
        Then I verify that `activityInfo.activityID` value has been updated on the contract on the `clone` machine
        When I run `pro enable fips-updates --assume-yes` `with sudo` on the `clone` machine
        When I run `pro status --format yaml` `with sudo` on the `clone` machine
        Then stdout matches regexp:
        """
          name: fips-updates
          status: enabled
        """
        When I reboot the machine: `clone`
        When I run `pro status --format yaml` `with sudo` on the `clone` machine
        Then stdout matches regexp:
        """
          name: fips-updates
          status: enabled
        """
        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
