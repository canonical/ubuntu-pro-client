Feature: License check timer only runs in environments where necessary

    @series.lts
    @uses.config.contract_token
    @uses.config.machine_type.gcp.generic
    Scenario Outline: license_check job should run periodically on gcp generic lts
        Given a `<release>` machine with ubuntu-advantage-tools installed
        # verify its enabled
        Then I verify the `ua-license-check` systemd timer is scheduled to run within `10` minutes
        # run it and verify that it didn't disable itself
        When I run `systemctl start ua-license-check.service` with sudo
        When I wait `5` seconds
        Then I verify the `ua-license-check` systemd timer is scheduled to run within `10` minutes
        # verify attach disables it
        When I wait `5` seconds
        When I attach `contract_token` with sudo
        Then I verify the `ua-license-check` systemd timer is disabled
        # verify detach enables it
        When I run `ua detach --assume-yes` with sudo
        Then I verify the `ua-license-check` systemd timer is scheduled to run within `10` minutes
        # verify stopping and deleting marker file and stopping disables it
        #   We need to call stop both before and after rm-ing the marker file
        #     because at least one version of systemd requires it before (245.4-4ubuntu3.11
        #     on focal gcp), and every other tested version of systemd requires it after
        #   But this is only necessary when manually running the steps or in this test.
        #     `disable_license_checks_if_applicable` works fine with only calling stop after,
        #     as evidenced by the "verify attach disables it" steps above passing on focal gcp.
        When I run `systemctl stop ua-license-check.timer` with sudo
        When I run `rm /var/lib/ubuntu-advantage/marker-license-check` with sudo
        When I run `systemctl stop ua-license-check.timer` with sudo
        Then I verify the `ua-license-check` systemd timer is disabled
        # verify creating marker file enables it
        When I run `touch /var/lib/ubuntu-advantage/marker-license-check` with sudo
        Then I verify the `ua-license-check` systemd timer is scheduled to run within `10` minutes
        Examples: version
            | release |
            | xenial  |
            | bionic  |
            | focal   |

    @series.hirsute
    @uses.config.contract_token
    @uses.config.machine_type.gcp.generic
    Scenario Outline: license_check is disabled gcp generic non lts
        Given a `<release>` machine with ubuntu-advantage-tools installed
        Then I verify the `ua-license-check` systemd timer is disabled
        # verify creating marker file enables it, but it disables itself
        When I run `touch /var/lib/ubuntu-advantage/marker-license-check` with sudo
        Then I verify the `ua-license-check` systemd timer either ran within the past `5` seconds OR is scheduled to run within `10` minutes
        When I run `systemctl start ua-license-check.service` with sudo
        When I wait `5` seconds
        Then I verify the `ua-license-check` systemd timer is disabled
        # verify attach and detach does not enable it
        When I wait `5` seconds
        When I attach `contract_token` with sudo
        When I run `ua detach --assume-yes` with sudo
        When I wait `5` seconds
        Then I verify the `ua-license-check` systemd timer is disabled
        Examples: version
            | release |
            | hirsute |

    @series.all
    @uses.config.contract_token
    @uses.config.machine_type.lxd.container
    @uses.config.machine_type.lxd.vm
    @uses.config.machine_type.aws.generic
    @uses.config.machine_type.azure.generic
    Scenario Outline: license_check is disabled everywhere but gcp generic
        Given a `<release>` machine with ubuntu-advantage-tools installed
        Then I verify the `ua-license-check` systemd timer is disabled
        When I reboot the `<release>` machine
        Then I verify the `ua-license-check` systemd timer is disabled
        # verify creating marker file enables it, but it disables itself
        When I run `touch /var/lib/ubuntu-advantage/marker-license-check` with sudo
        Then I verify the `ua-license-check` systemd timer either ran within the past `5` seconds OR is scheduled to run within `10` minutes
        When I run `systemctl start ua-license-check.service` with sudo
        When I wait `5` seconds
        And I verify that running `grep "Disabling gcp_auto_attach job" /var/log/ubuntu-advantage-license-check.log` `with sudo` exits `0`
        And I verify that running `grep "Disabling gcp_auto_attach job" /var/log/ubuntu-advantage.log` `with sudo` exits `1`
        Then I verify the `ua-license-check` systemd timer is disabled
        # verify attach and detach does not enable it
        When I wait `5` seconds
        When I attach `contract_token` with sudo
        When I run `ua detach --assume-yes` with sudo
        When I wait `5` seconds
        Then I verify the `ua-license-check` systemd timer is disabled
        Examples: version
            | release |
            | xenial  |
            | bionic  |
            | focal   |
            | hirsute |
            | impish  |

    @series.lts
    @uses.config.machine_type.aws.pro
    @uses.config.machine_type.azure.pro
    @uses.config.machine_type.gcp.pro
    Scenario Outline: license_check is disabled everywhere but gcp generic
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        When I run `ua auto-attach` with sudo
        Then I verify the `ua-license-check` systemd timer is disabled
        # verify creating marker file enables it, but it disables itself
        When I run `touch /var/lib/ubuntu-advantage/marker-license-check` with sudo
        Then I verify the `ua-license-check` systemd timer either ran within the past `5` seconds OR is scheduled to run within `10` minutes
        When I run `systemctl start ua-license-check.service` with sudo
        When I wait `5` seconds
        Then I verify the `ua-license-check` systemd timer is disabled
        Examples: version
            | release |
            | xenial  |
            | bionic  |
            | focal   |
