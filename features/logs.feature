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
