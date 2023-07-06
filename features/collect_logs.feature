Feature: Command behaviour when attached to an Ubuntu Pro subscription

    @series.all
    @uses.config.machine_type.lxd-container
    Scenario Outline: Run collect-logs on an unattached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        # simulate logrotate
        When I run `touch /var/log/ubuntu-advantage.log.1` with sudo
        When I run `touch /var/log/ubuntu-advantage.log.2.gz` with sudo
        When I run `touch /var/log/ubuntu-advantage-timer.log.1` with sudo
        When I run `touch /var/log/ubuntu-advantage-timer.log.2.gz` with sudo
        When I run `pro collect-logs` with sudo
        Then I verify that files exist matching `ua_logs.tar.gz`
        When I run `tar zxf ua_logs.tar.gz` as non-root
        Then I verify that files exist matching `logs/`
        When I run `sh -c "ls -1 logs/ | sort -d"` as non-root
        # On Xenial, the return value for inexistent services is the same as for dead ones (3).
        # So the -error suffix does not appear there.
        Then stdout matches regexp:
        """
        build.info
        cloud-id.txt
        jobs-status.json
        journalctl.txt
        livepatch-status.txt-error
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
        ubuntu-advantage-timer.log
        ubuntu-advantage-timer.log.1
        ubuntu-advantage-timer.log.2.gz
        """
        Examples: ubuntu release
          | release |
          | xenial  |
          | bionic  |
          | focal   |
          | jammy   |
          | kinetic |
          | lunar   |
          | mantic  |

    @series.lts
    @uses.config.machine_type.lxd-container
    @uses.config.contract_token
    Scenario Outline: Run collect-logs on an attached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        # simulate logrotate
        When I run `touch /var/log/ubuntu-advantage.log.1` with sudo
        When I run `touch /var/log/ubuntu-advantage.log.2.gz` with sudo
        When I run `touch /var/log/ubuntu-advantage-timer.log.1` with sudo
        When I run `touch /var/log/ubuntu-advantage-timer.log.2.gz` with sudo
        When I run `pro collect-logs` with sudo
        Then I verify that files exist matching `ua_logs.tar.gz`
        When I run `tar zxf ua_logs.tar.gz` as non-root
        Then I verify that files exist matching `logs/`
        When I run `sh -c "ls -1 logs/ | sort -d"` as non-root
        # On Xenial, the return value for inexistent services is the same as for dead ones (3).
        # So the -error suffix does not appear there.
        Then stdout matches regexp:
        """
        build.info
        cloud-id.txt
        jobs-status.json
        journalctl.txt
        livepatch-status.txt-error
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
        ubuntu-advantage-timer.log
        ubuntu-advantage-timer.log.1
        ubuntu-advantage-timer.log.2.gz
        ubuntu-esm-apps.list
        ubuntu-esm-infra.list
        """
        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | jammy   |
