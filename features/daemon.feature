Feature: Pro Upgrade Daemon only runs in environments where necessary

  @uses.config.contract_token
  Scenario Outline: cloud-id-shim service is not installed on anything other than xenial
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    Then I verify that running `systemctl status ubuntu-advantage-cloud-id-shim.service` `with sudo` exits `4`
    Then stderr matches regexp:
      """
      Unit ubuntu-advantage-cloud-id-shim.service could not be found.
      """

    Examples: version
      | release | machine_type  |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | mantic  | lxd-container |
      | noble   | lxd-container |

  @uses.config.contract_token
  Scenario Outline: cloud-id-shim should run in postinst and on boot
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
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
      | release | machine_type  |
      | xenial  | lxd-container |

  @uses.config.contract_token
  Scenario Outline: daemon should run when appropriate on gcp generic lts
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    # verify its enabled, but stops itself when not configured to poll
    When I run `journalctl -o cat -u ubuntu-advantage.service` with sudo
    Then stdout contains substring:
      """
      daemon starting
      """
    Then stdout contains substring:
      """
      Configured to not poll for pro license, shutting down
      """
    Then stdout contains substring:
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
    When I create the file `/var/lib/ubuntu-advantage/private/user-config.json` with the following:
      """
      { "poll_for_pro_license": true }
      """
    # Turn on memory accounting
    When I run `sed -i s/#DefaultMemoryAccounting=no/DefaultMemoryAccounting=yes/ /etc/systemd/system.conf` with sudo
    When I run `systemctl daemon-reexec` with sudo
    # on bionic, systemd version=237; which does not allow for log rotation + vacuum in same line e.g.
    # journalctl --flush --rotate --vacuum-time=1s
    When I run `journalctl --flush --rotate` with sudo
    When I run `journalctl --vacuum-time=1s` with sudo
    When I run `systemctl restart ubuntu-advantage.service` with sudo
    # wait to get memory after it has settled/after startup checks
    When I wait `5` seconds
    Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `0`
    Then stdout matches regexp:
      """
      Active: active \(running\)
      """
    # TODO find out what caused memory to go up, try to lower it again
    Then on `xenial`, systemd status output says memory usage is less than `18` MB
    Then on `bionic`, systemd status output says memory usage is less than `15` MB
    Then on `focal`, systemd status output says memory usage is less than `14` MB
    Then on `jammy`, systemd status output says memory usage is less than `14` MB
    Then on `noble`, systemd status output says memory usage is less than `17` MB
    When I run `journalctl -o cat -u ubuntu-advantage.service` with sudo
    Then stdout contains substring:
      """
      daemon starting
      """
    Then stdout does not contain substring:
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
      \s*Condition: start condition (failed|unmet).*
      .*ConditionPathExists=!/var/lib/ubuntu-advantage/private/machine-token.json was not met
      """
    # verify detach starts it and it starts again after reboot
    When I run `journalctl --flush --rotate` with sudo
    When I run `journalctl --vacuum-time=1s` with sudo
    When I run `pro detach --assume-yes` with sudo
    Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `0`
    Then stdout matches regexp:
      """
      Active: active \(running\)
      """
    When I run `journalctl -o cat -u ubuntu-advantage.service` with sudo
    Then stdout contains substring:
      """
      daemon starting
      """
    Then stdout does not contain substring:
      """
      daemon ending
      """
    When I reboot the machine
    Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `0`
    Then stdout matches regexp:
      """
      Active: active \(running\)
      """
    When I run `journalctl -o cat -u ubuntu-advantage.service` with sudo
    Then stdout contains substring:
      """
      daemon starting
      """
    Then stdout does not contain substring:
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
      | release | machine_type |
      | xenial  | gcp.generic  |
      | bionic  | gcp.generic  |
      | focal   | gcp.generic  |
      | jammy   | gcp.generic  |
      | noble   | gcp.generic  |

  @uses.config.contract_token
  Scenario Outline: daemon should run when appropriate on azure generic lts
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    # verify its enabled, but stops itself when not configured to poll
    When I run `journalctl -o cat -u ubuntu-advantage.service` with sudo
    Then stdout contains substring:
      """
      daemon starting
      """
    Then stdout contains substring:
      """
      Configured to not poll for pro license, shutting down
      """
    Then stdout contains substring:
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
    When I create the file `/var/lib/ubuntu-advantage/private/user-config.json` with the following:
      """
      { "poll_for_pro_license": true }
      """
    When I run `systemctl restart ubuntu-advantage.service` with sudo
    # give it time to get past the initial request
    When I wait `5` seconds
    When I run `journalctl -o cat -u ubuntu-advantage.service` with sudo
    Then stdout contains substring:
      """
      daemon starting
      """
    Then stdout contains substring:
      """
      Cancelling polling
      """
    Then stdout contains substring:
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

    Examples: version
      | release | machine_type  |
      | xenial  | azure.generic |
      | bionic  | azure.generic |
      | focal   | azure.generic |
      | jammy   | azure.generic |
      | noble   | azure.generic |

  @uses.config.contract_token
  Scenario Outline: daemon does not start on gcp,azure generic non lts
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I wait `1` seconds
    When I run `journalctl -o cat -u ubuntu-advantage.service` with sudo
    Then stdout contains substring:
      """
      daemon starting
      """
    Then stdout contains substring:
      """
      Not on LTS, shutting down
      """
    Then stdout contains substring:
      """
      daemon ending
      """

    Examples: version
      | release | machine_type  |
      | mantic  | azure.generic |
      | mantic  | gcp.generic   |

  @uses.config.contract_token
  Scenario Outline: daemon does not start when not on gcpgeneric or azuregeneric
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `3`
    Then stdout matches regexp:
      """
      Active: inactive \(dead\)
      \s*Condition: start condition (failed|unmet).*
      """
    When I attach `contract_token` with sudo
    When I run `pro detach --assume-yes` with sudo
    When I reboot the machine
    Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `3`
    Then stdout matches regexp:
      """
      Active: inactive \(dead\)
      \s*Condition: start condition (failed|unmet).*
      """

    Examples: version
      | release | machine_type  |
      | xenial  | lxd-container |
      | xenial  | lxd-vm        |
      | xenial  | aws.generic   |
      | bionic  | lxd-container |
      | bionic  | lxd-vm        |
      | bionic  | aws.generic   |
      | focal   | lxd-container |
      | focal   | lxd-vm        |
      | focal   | aws.generic   |
      | jammy   | lxd-container |
      | jammy   | lxd-vm        |
      | jammy   | aws.generic   |
      | mantic  | lxd-container |
      | mantic  | lxd-vm        |
      | mantic  | aws.generic   |
      | noble   | lxd-container |
      | noble   | lxd-vm        |
      | noble   | aws.generic   |

  Scenario Outline: daemon does not start when not on gcpgeneric or azuregeneric
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
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
    When I reboot the machine
    Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `3`
    Then stdout matches regexp:
      """
      Active: inactive \(dead\)
      \s*Condition: start condition failed.*
      """

    Examples: version
      | release | machine_type |
      | xenial  | aws.pro      |
      | bionic  | aws.pro      |
      | focal   | aws.pro      |

  Scenario Outline: daemon does not start when not on gcpgeneric or azuregeneric
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
      """
      contract_url: 'https://contracts.canonical.com'
      data_dir: /var/lib/ubuntu-advantage
      log_level: debug
      log_file: /var/log/ubuntu-advantage.log
      """
    When I run `pro auto-attach` with sudo
    When I run `journalctl --flush --rotate` with sudo
    When I run `journalctl --vacuum-time=1s` with sudo
    When I run `systemctl restart ubuntu-advantage.service` with sudo
    Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `3`
    Then stdout matches regexp:
      """
      Active: inactive \(dead\).*
      \s*Condition: start condition failed.*
      """
    When I run `journalctl -o cat -u ubuntu-advantage.service` with sudo
    Then stdout does not contain substring:
      """
      daemon starting
      """
    When I reboot the machine
    Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `3`
    Then stdout matches regexp:
      """
      Active: inactive \(dead\)
      \s*Condition: start condition failed.*
      """
    When I run `journalctl -o cat -u ubuntu-advantage.service` with sudo
    Then stdout does not contain substring:
      """
      daemon starting
      """

    Examples: version
      | release | machine_type |
      | xenial  | azure.pro    |
      | xenial  | gcp.pro      |
      | bionic  | azure.pro    |
      | bionic  | gcp.pro      |
      | focal   | azure.pro    |
      | focal   | gcp.pro      |

  @skip_local_environment @skip_prebuilt_environment @uses.config.contract_token
  Scenario Outline: daemon should wait for cloud-config.service to finish
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed adding this cloud-init user_data
      """
      ubuntu_advantage: {}
      """
    When I apt remove `ubuntu-advantage-tools ubuntu-pro-client`
    When I run `cloud-init clean --logs` with sudo
    When I reboot the machine
    When I run `journalctl -b -o cat -u ubuntu-advantage.service` with sudo
    Then stdout contains substring:
      """
      daemon starting
      """
    Then stdout does not contain substring:
      """
      daemon ending
      """
    When I wait `20` seconds
    When I run `journalctl -b -o cat -u ubuntu-advantage.service` with sudo
    Then stdout contains substring:
      """
      daemon ending
      """

    Examples: version
      | release | machine_type |
      | bionic  | gcp.generic  |
      | focal   | gcp.generic  |
      | jammy   | gcp.generic  |
