Feature: CLI collect-logs command

  @arm64
  Scenario Outline: Run collect-logs on an unattached machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
    # simulate logrotate
    When I run `touch /var/log/ubuntu-advantage.log.1` with sudo
    When I run `touch /var/log/ubuntu-advantage.log.2.gz` with sudo
    When I run `pro collect-logs` <user_spec>
    Then I verify that files exist matching `pro_logs.tar.gz`
    When I run `tar zxf pro_logs.tar.gz` with sudo
    Then I verify that files exist matching `logs/`
    When I run `sh -c "ls -1 logs/ | sort -d"` with sudo
    # On Xenial, the return value for inexistent services is the same as for dead ones (3).
    # So the -error suffix does not appear there.
    Then stdout matches regexp:
      """
      apt-news.service.txt
      build.info
      cloud-id.txt
      cloud-init-journal.txt
      environment_vars.json
      esm-cache.service.txt
      jobs-status.json
      livepatch-status.txt-error
      pro-journal.txt
      pro-status.json
      systemd-timers.txt
      ua-auto-attach.path.txt(-error)?
      ua-auto-attach.service.txt(-error)?
      uaclient.conf
      ua-reboot-cmds.service.txt
      ua-timer.service.txt
      ua-timer.timer.txt
      ubuntu-advantage.log
      ubuntu-advantage.log.1
      ubuntu-advantage.log.2.gz
      ubuntu-advantage.service.txt
      """
    When I verify that running `pro collect-logs -o pro_logs.tar.gz` `with sudo` exits `1`
    Then stderr matches regexp:
      """
      The file pro_logs.tar.gz already exists in the system.
      """
    When I run `rm pro_logs.tar.gz` with sudo
    And I run `pro collect-logs` <user_spec>
    Then I verify that files exist matching `pro_logs.tar.gz`

    Examples: ubuntu release
      | release  | machine_type  | user_spec   |
      | xenial   | lxd-container | as non-root |
      | bionic   | lxd-container | as non-root |
      | focal    | lxd-container | as non-root |
      | jammy    | lxd-container | as non-root |
      | noble    | lxd-container | with sudo   |
      | plucky   | lxd-container | with sudo   |
      | questing | lxd-container | with sudo   |

  @uses.config.contract_token @arm64
  Scenario Outline: Run collect-logs on an attached machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
    # simulate logrotate
    When I run `touch /var/log/ubuntu-advantage.log.1` with sudo
    When I run `touch /var/log/ubuntu-advantage.log.2.gz` with sudo
    When I run `pro collect-logs` <user_spec>
    Then I verify that files exist matching `pro_logs.tar.gz`
    When I run `tar zxf pro_logs.tar.gz` as non-root
    Then I verify that files exist matching `logs/`
    When I run `sh -c "ls -1 logs/ | sort -d"` as non-root
    # On Xenial, the return value for inexistent services is the same as for dead ones (3).
    # So the -error suffix does not appear there.
    Then stdout matches regexp:
      """
      apt-news.service.txt
      build.info
      cloud-id.txt
      cloud-init-journal.txt
      environment_vars.json
      esm-cache.service.txt
      jobs-status.json
      livepatch-status.txt-error
      pro-journal.txt
      pro-status.json
      systemd-timers.txt
      ua-auto-attach.path.txt(-error)?
      ua-auto-attach.service.txt(-error)?
      uaclient.conf
      ua-reboot-cmds.service.txt
      ua-timer.service.txt
      ua-timer.timer.txt
      ubuntu-advantage.log
      ubuntu-advantage.log.1
      ubuntu-advantage.log.2.gz
      ubuntu-advantage.service.txt
      ubuntu-esm-apps.(list|sources)
      ubuntu-esm-infra.(list|sources)
      """
    When I verify that running `pro collect-logs -o pro_logs.tar.gz` `with sudo` exits `1`
    Then stderr matches regexp:
      """
      The file pro_logs.tar.gz already exists in the system.
      """
    When I verify that running `pro collect-logs -o pro_logs.tar.gz` `with sudo` exits `1`
    Then stderr matches regexp:
      """
      The file pro_logs.tar.gz already exists in the system.
      """
    When I run `rm pro_logs.tar.gz` with sudo
    And I run `pro collect-logs` <user_spec>
    Then I verify that files exist matching `pro_logs.tar.gz`

    Examples: ubuntu release
      | release | machine_type  | user_spec   |
      | xenial  | lxd-container | as non-root |
      | bionic  | lxd-container | as non-root |
      | focal   | lxd-container | as non-root |
      | jammy   | lxd-container | as non-root |
      | noble   | lxd-container | with sudo   |
