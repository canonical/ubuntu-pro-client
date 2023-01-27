Feature: Pro Upgrade Daemon only runs in environments where necessary

    @series.all
    @uses.config.contract_token
    @uses.config.machine_type.lxd.container
    Scenario Outline: cloud-id-shim service is not installed on anything other than xenial
        Given a `<release>` machine with ubuntu-advantage-tools installed
        Then I verify that running `systemctl status ubuntu-advantage-cloud-id-shim.service` `with sudo` exits `4`
        Then stderr matches regexp:
        """
        Unit ubuntu-advantage-cloud-id-shim.service could not be found.
        """
        Examples: version
            | release |
            | bionic  |
            | focal   |
            | jammy   |
            | kinetic |
            | lunar   |

    @series.lts
    @uses.config.contract_token
    @uses.config.machine_type.lxd.container
    Scenario Outline: cloud-id-shim should run in postinst and on boot
        Given a `<release>` machine with ubuntu-advantage-tools installed
        # verify installing pro created the cloud-id file
        When I run `cat /run/cloud-init/cloud-id` with sudo
        Then I will see the following on stdout
        """
        lxd
        """
        When I run `cat /run/cloud-init/cloud-id-lxd` with sudo
        Then I will see the following on stdout
        """
        lxd
        """
        # verify the shim service runs on boot and creates the cloud-id file
        When I reboot the machine
        Then I verify that running `systemctl status ubuntu-advantage-cloud-id-shim.service` `with sudo` exits `3`
        Then stdout matches regexp:
        """
        (code=exited, status=0/SUCCESS)
        """
        When I run `cat /run/cloud-init/cloud-id` with sudo
        Then I will see the following on stdout
        """
        lxd
        """
        When I run `cat /run/cloud-init/cloud-id-lxd` with sudo
        Then I will see the following on stdout
        """
        lxd
        """
        Examples: version
            | release |
            | xenial  |

    @series.lts
    @uses.config.contract_token
    @uses.config.machine_type.gcp.generic
    Scenario Outline: daemon should run when appropriate on gcp generic lts
        Given a `<release>` machine with ubuntu-advantage-tools installed
        # verify its enabled, but stops itself when not configured to poll
        When I run `cat /var/log/ubuntu-advantage-daemon.log` with sudo
        Then stdout matches regexp:
        """
        daemon starting
        """
        Then stdout matches regexp:
        """
        Configured to not poll for pro license, shutting down
        """
        Then stdout matches regexp:
        """
        daemon ending
        """
        When I run `systemctl is-enabled ubuntu-advantage.service` with sudo
        Then stdout matches regexp:
        """
        enabled
        """
        Then I verify that running `systemctl is-failed ubuntu-advantage.service` `with sudo` exits `1`
        Then stdout matches regexp:
        """
        inactive
        """

        # verify it stays on when configured to do so
        When I create the file `/var/lib/ubuntu-advantage/user-config.json` with the following:
        """
        { "poll_for_pro_license": true }
        """
        # Turn on memory accounting
        When I run `sed -i s/#DefaultMemoryAccounting=no/DefaultMemoryAccounting=yes/ /etc/systemd/system.conf` with sudo
        When I run `systemctl daemon-reexec` with sudo

        When I run `truncate -s 0 /var/log/ubuntu-advantage-daemon.log` with sudo
        When I run `systemctl restart ubuntu-advantage.service` with sudo

        # wait to get memory after it has settled/after startup checks
        When I wait `5` seconds
        Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `0`
        Then stdout matches regexp:
        """
        Active: active \(running\)
        """
        # TODO find out what caused memory to go up, try to lower it again
        Then on `xenial`, systemd status output says memory usage is less than `16` MB
        Then on `bionic`, systemd status output says memory usage is less than `14` MB
        Then on `focal`, systemd status output says memory usage is less than `12` MB
        Then on `jammy`, systemd status output says memory usage is less than `13` MB

        When I run `cat /var/log/ubuntu-advantage-daemon.log` with sudo
        Then stdout matches regexp:
        """
        daemon starting
        """
        Then stdout does not match regexp:
        """
        daemon ending
        """
        When I run `systemctl is-enabled ubuntu-advantage.service` with sudo
        Then stdout matches regexp:
        """
        enabled
        """
        Then I verify that running `systemctl is-failed ubuntu-advantage.service` `with sudo` exits `1`
        Then stdout matches regexp:
        """
        active
        """

        # verify attach stops it immediately and doesn't restart after reboot
        When I attach `contract_token` with sudo
        Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `3`
        Then stdout matches regexp:
        """
        Active: inactive \(dead\)
        """
        When I reboot the machine
        Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `3`
        Then stdout matches regexp:
        """
        Active: inactive \(dead\)
        \s*Condition: start condition failed.*
        .*ConditionPathExists=!/var/lib/ubuntu-advantage/private/machine-token.json was not met
        """

        # verify detach starts it and it starts again after reboot
        When I run `truncate -s 0 /var/log/ubuntu-advantage-daemon.log` with sudo
        When I run `pro detach --assume-yes` with sudo
        Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `0`
        Then stdout matches regexp:
        """
        Active: active \(running\)
        """
        When I run `cat /var/log/ubuntu-advantage-daemon.log` with sudo
        Then stdout matches regexp:
        """
        daemon starting
        """
        Then stdout does not match regexp:
        """
        daemon ending
        """
        When I reboot the machine
        Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `0`
        Then stdout matches regexp:
        """
        Active: active \(running\)
        """
        When I run `cat /var/log/ubuntu-advantage-daemon.log` with sudo
        Then stdout matches regexp:
        """
        daemon starting
        """
        Then stdout does not match regexp:
        """
        daemon ending
        """

        # Verify manual stop & disable persists across reconfigure
        When I run `systemctl stop ubuntu-advantage.service` with sudo
        When I run `systemctl disable ubuntu-advantage.service` with sudo
        Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `3`
        Then stdout matches regexp:
        """
        Active: inactive \(dead\)
        """
        When I run `dpkg-reconfigure ubuntu-advantage-tools` with sudo
        Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `3`
        Then stdout matches regexp:
        """
        Active: inactive \(dead\)
        """

        # Verify manual stop & disable persists across reboot
        When I reboot the machine
        Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `3`
        Then stdout matches regexp:
        """
        Active: inactive \(dead\)
        """
        Examples: version
            | release |
            | xenial  |
            | bionic  |
            | focal   |
            | jammy   |

    @series.kinetic
    @uses.config.contract_token
    @uses.config.machine_type.gcp.generic
    Scenario Outline: daemon does not start on gcp generic non lts
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I wait `1` seconds
        When I run `cat /var/log/ubuntu-advantage-daemon.log` with sudo
        Then stdout matches regexp:
        """
        daemon starting
        """
        Then stdout matches regexp:
        """
        Not on LTS, shutting down
        """
        Then stdout matches regexp:
        """
        daemon ending
        """
        Examples: version
            | release |
            | kinetic |

    @series.all
    @uses.config.contract_token
    @uses.config.machine_type.lxd.container
    @uses.config.machine_type.lxd.vm
    @uses.config.machine_type.aws.generic
    @uses.config.machine_type.azure.generic
    Scenario Outline: daemon does not start when not on gcpgeneric
        Given a `<release>` machine with ubuntu-advantage-tools installed
        Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `3`
        Then stdout matches regexp:
        """
        Active: inactive \(dead\)
        \s*Condition: start condition failed.*
        """
        Then I verify that running `cat /var/log/ubuntu-advantage-daemon.log` `with sudo` exits `1`
        When I attach `contract_token` with sudo
        When I run `pro detach --assume-yes` with sudo
        When I reboot the machine
        Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `3`
        Then stdout matches regexp:
        """
        Active: inactive \(dead\)
        \s*Condition: start condition failed.*
        """
        Then I verify that running `cat /var/log/ubuntu-advantage-daemon.log` `with sudo` exits `1`
        Examples: version
            | release |
            | xenial  |
            | bionic  |
            | focal   |
            | jammy   |
            | kinetic |

    @series.lts
    @uses.config.machine_type.aws.pro
    @uses.config.machine_type.azure.pro
    Scenario Outline: daemon does not start when not on gcpgeneric
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        When I run `pro auto-attach` with sudo
        When I run `systemctl restart ubuntu-advantage.service` with sudo
        Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `3`
        Then stdout matches regexp:
        """
        Active: inactive \(dead\)
        \s*Condition: start condition failed.*
        """
        Then I verify that running `cat /var/log/ubuntu-advantage-daemon.log` `with sudo` exits `1`
        When I reboot the machine
        Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `3`
        Then stdout matches regexp:
        """
        Active: inactive \(dead\)
        \s*Condition: start condition failed.*
        """
        Then I verify that running `cat /var/log/ubuntu-advantage-daemon.log` `with sudo` exits `1`
        Examples: version
            | release |
            | xenial  |
            | bionic  |
            | focal   |

    @series.lts
    @uses.config.machine_type.gcp.pro
    Scenario Outline: daemon does not start when not on gcpgeneric
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        When I run `pro auto-attach` with sudo
        When I run `truncate -s 0 /var/log/ubuntu-advantage-daemon.log` with sudo
        When I run `systemctl restart ubuntu-advantage.service` with sudo
        Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `3`
        Then stdout matches regexp:
        """
        Active: inactive \(dead\).*
        \s*Condition: start condition failed.*
        .*ConditionPathExists=!/var/lib/ubuntu-advantage/private/machine-token.json was not met
        """
        When I run `cat /var/log/ubuntu-advantage-daemon.log` with sudo
        Then stdout does not match regexp:
        """
        daemon starting
        """
        When I reboot the machine
        Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `3`
        Then stdout matches regexp:
        """
        Active: inactive \(dead\)
        \s*Condition: start condition failed.*
        .*ConditionPathExists=!/var/lib/ubuntu-advantage/private/machine-token.json was not met
        """
        When I run `cat /var/log/ubuntu-advantage-daemon.log` with sudo
        Then stdout does not match regexp:
        """
        daemon starting
        """
        Examples: version
            | release |
            | xenial  |
            | bionic  |
            | focal   |
