Feature: Command behaviour when attached to an Ubuntu Pro subscription

    Scenario Outline: Run collect-logs on an unattached machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        # simulate logrotate
        When I run `touch /var/log/ubuntu-advantage.log.1` with sudo
        When I run `touch /var/log/ubuntu-advantage.log.2.gz` with sudo
        When I run `pro collect-logs` as non-root
        Then I verify that files exist matching `ua_logs.tar.gz`
        When I run `tar zxf ua_logs.tar.gz` with sudo
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
        esm-cache.service.txt
        jobs-status.json
        livepatch-status.txt-error
        pro-journal.txt
        systemd-timers.txt
        ua-auto-attach.path.txt(-error)?
        ua-auto-attach.service.txt(-error)?
        uaclient.conf
        ua-reboot-cmds.service.txt
        ua-status.json
        ua-timer.service.txt
        ua-timer.timer.txt
        ubuntu-advantage.log
        ubuntu-advantage.log.1
        ubuntu-advantage.log.2.gz
        ubuntu-advantage.service.txt
        """
        Examples: ubuntu release
          | release | machine_type  |
          | xenial  | lxd-container |
          | bionic  | lxd-container |
          | focal   | lxd-container |
          | jammy   | lxd-container |
          | mantic  | lxd-container |

    @uses.config.contract_token
    Scenario Outline: Run collect-logs on an attached machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        # simulate logrotate
        When I run `touch /var/log/ubuntu-advantage.log.1` with sudo
        When I run `touch /var/log/ubuntu-advantage.log.2.gz` with sudo
        When I run `pro collect-logs` as non-root
        Then I verify that files exist matching `ua_logs.tar.gz`
        When I run `tar zxf ua_logs.tar.gz` as non-root
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
        esm-cache.service.txt
        jobs-status.json
        livepatch-status.txt-error
        pro-journal.txt
        systemd-timers.txt
        ua-auto-attach.path.txt(-error)?
        ua-auto-attach.service.txt(-error)?
        uaclient.conf
        ua-reboot-cmds.service.txt
        ua-status.json
        ua-timer.service.txt
        ua-timer.timer.txt
        ubuntu-advantage.log
        ubuntu-advantage.log.1
        ubuntu-advantage.log.2.gz
        ubuntu-advantage.service.txt
        ubuntu-esm-apps.list
        ubuntu-esm-infra.list
        """
        Examples: ubuntu release
           | release | machine_type  |
           | xenial  | lxd-container |
           | bionic  | lxd-container |
           | focal   | lxd-container |
           | jammy   | lxd-container |
