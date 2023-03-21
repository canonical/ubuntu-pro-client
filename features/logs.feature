Feature: Logs in Json Array Formatter

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: The log file can be successfully parsed as json array
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt update` with sudo
        And I run `apt install jq -y` with sudo
        And I verify that running `pro status` `with sudo` exits `0`
        And I verify that running `pro enable test_entitlement` `with sudo` exits `1`
        And I run shell command `tail /var/log/ubuntu-advantage.log | jq -r .` as non-root
        Then I will see the following on stderr
        """
        """
        When I attach `contract_token` with sudo
        And I verify that running `pro refresh` `with sudo` exits `0`
        And I verify that running `pro status` `with sudo` exits `0`
        And I verify that running `pro enable test_entitlement` `with sudo` exits `1`
        And I run shell command `tail /var/log/ubuntu-advantage.log | jq -r .` as non-root
        Then I will see the following on stderr
        """
        """
        Examples: ubuntu release
          | release |
          | xenial  |
          | bionic  |
          | focal   |
          | kinetic |
          | jammy   |
          | lunar   |

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Non-root user and root user log files are different
        Given a `<release>` machine with ubuntu-advantage-tools installed
        # Confirm user log file does not exist 
        When I verify `/var/log/ubuntu-advantage.log` is empty
        Then I verify that no files exist matching `/home/ubuntu/.cache/ubuntu-pro/ubuntu-pro.log`
        When I verify that running `pro status` `as non-root` exits `0`
        Then I verify that files exist matching `/home/ubuntu/.cache/ubuntu-pro/ubuntu-pro.log`
        When I verify `/var/log/ubuntu-advantage.log` is empty
        And I run `cat /home/ubuntu/.cache/ubuntu-pro/ubuntu-pro.log` as non-root
        Then stdout contains substring
        """
        Executed with sys.argv: ['/usr/bin/pro', 'status']
        """
        When I run `truncate -s 0 /home/ubuntu/.cache/ubuntu-pro/ubuntu-pro.log` with sudo
        And I attach `contract_token` with sudo
        And I verify `/home/ubuntu/.cache/ubuntu-pro/ubuntu-pro.log` is empty
        And I run `cat /var/log/ubuntu-advantage.log` as non-root
        Then stdout contains substring
        """
        Executed with sys.argv: ['/usr/bin/pro', 'attach'
        """
        Examples: ubuntu release
          | release |
          | xenial  |
          | bionic  |
          | focal   |
          | kinetic |
          | jammy   |
          | lunar   |

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Non-root user log files included in collect logs
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When i verify that running `pro status` `with sudo` exits `0`
        And I verify that running `pro collect-logs` `with sudo` exits `0`
        And I run `tar -tf ua_logs.tar.gz` as non-root
        Then stdout does not contain substring 
        """
        user0.log
        """
        When i verify that running `pro status` `as non-root` exits `0`
        And I verify that running `pro collect-logs` `with sudo` exits `0`
        And I run `tar -tf ua_logs.tar.gz` as non-root
        Then stdout contains substring 
        """
        user0.log
        """
        Examples: ubuntu release
          | release |
          | xenial  |
          | bionic  |
          | focal   |
          | kinetic |
          | jammy   |
          | lunar   |
