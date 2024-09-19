Feature: Full Auto-Attach Endpoint

  Scenario Outline: Run auto-attach on cloud instance.
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
      """
      contract_url: 'https://contracts.canonical.com'
      data_dir: /var/lib/ubuntu-advantage
      log_level: debug
      log_file: /var/log/ubuntu-advantage.log
      """
    When I create the file `/tmp/full_auto_attach.py` with the following:
      """
      from uaclient.api.u.pro.attach.auto.full_auto_attach.v1 import full_auto_attach, FullAutoAttachOptions

      full_auto_attach(FullAutoAttachOptions(enable=["esm-infra"]))
      """
    And I run `python3 /tmp/full_auto_attach.py` with sudo
    Then I verify that `esm-infra` is enabled
    And I verify that `livepatch` is disabled

    Examples:
      | release | machine_type |
      | xenial  | aws.pro      |
      | xenial  | azure.pro    |
      | xenial  | gcp.pro      |
      | bionic  | aws.pro      |
      | bionic  | azure.pro    |
      | bionic  | gcp.pro      |
      | focal   | aws.pro      |
      | focal   | azure.pro    |
      | focal   | gcp.pro      |
      | jammy   | aws.pro      |
      | jammy   | azure.pro    |
      | jammy   | gcp.pro      |
      | noble   | aws.pro      |
      | noble   | azure.pro    |
      | noble   | gcp.pro      |
