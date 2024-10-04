Feature: YAML related interactions with Pro client

  # Services fail, degraded systemctl, but no crashes.
  Scenario Outline: services fail gracefully when yaml is broken/absent
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `rm -rf /usr/lib/python3/dist-packages/yaml` with sudo
    And I verify that running `pro status` `with sudo` exits `1`
    Then stderr matches regexp:
      """
      Couldn't import the YAML module.
      Make sure the 'python3-yaml' package is installed correctly
      and \/usr\/lib\/python3\/dist-packages is in your PYTHONPATH\.
      """
    When I verify that running `python3 /usr/lib/ubuntu-advantage/esm_cache.py` `with sudo` exits `1`
    Then stderr matches regexp:
      """
      Couldn't import the YAML module.
      Make sure the 'python3-yaml' package is installed correctly
      and \/usr\/lib\/python3\/dist-packages is in your PYTHONPATH\.
      """
    When I verify that running `systemctl start apt-news.service` `with sudo` exits `1`
    And I verify that running `systemctl start esm-cache.service` `with sudo` exits `1`
    And I run `systemctl --failed` with sudo
    Then stdout matches regexp:
      """
      apt-news.service
      """
    And stdout matches regexp:
      """
      esm-cache.service
      """
    When I apt install `python3-pip`
    And I run `pip3 install pyyaml==3.10` with sudo
    And I run `ls /usr/local/lib/<python_version>/dist-packages/` with sudo
    Then stdout matches regexp:
      """
      yaml
      """
    And I verify that running `pro status` `with sudo` exits `1`
    Then stderr matches regexp:
      """
      Error while trying to parse a yaml file using 'yaml' from
      """
    # Test the specific script which triggered LP #2007241
    When I verify that running `python3 /usr/lib/ubuntu-advantage/esm_cache.py` `with sudo` exits `1`
    Then stderr matches regexp:
      """
      Error while trying to parse a yaml file using 'yaml' from
      """
    When I verify that running `systemctl start apt-news.service` `with sudo` exits `1`
    And I verify that running `systemctl start esm-cache.service` `with sudo` exits `1`
    And I run `systemctl --failed` with sudo
    Then stdout matches regexp:
      """
      apt-news.service
      """
    And stdout matches regexp:
      """
      esm-cache.service
      """
    # Known crash that can happen but we don't care about for this test because it isn't pro related
    When I run shell command `rm -f /var/crash/_usr_bin_cloud-id.*.crash` with sudo
    When I run `ls /var/crash` with sudo
    Then I will see the following on stdout
      """
      """

    Examples: ubuntu release
      | release | machine_type  | python_version |
      | jammy   | lxd-container | python3.10     |
