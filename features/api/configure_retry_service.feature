Feature: api.u.pro.attach.auto.configure_retry_service

  Scenario Outline: v1 successfully triggers retry service when run during startup
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I change contract to staging with sudo
    When I create the file `/lib/systemd/system/apitest.service` with the following
      """
      [Unit]
      Description=test
      Before=ubuntu-advantage.service

      [Service]
      Type=oneshot
      ExecStart=/usr/bin/pro api u.pro.attach.auto.configure_retry_service.v1

      [Install]
      WantedBy=multi-user.target
      """
    When I run `systemctl enable apitest.service` with sudo
    When I reboot the machine
    # Cloud init may take a while here
    And I wait `15` seconds
    Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `0`
    Then stdout matches regexp:
      """
      Active: active \(running\)
      """
    Then stdout matches regexp:
      """
      mode: retry auto attach
      """
    Then stdout does not match regexp:
      """
      mode: poll for pro license
      """
    When I run `run-parts /etc/update-motd.d/` with sudo
    Then stdout matches regexp:
      """
      Failed to automatically attach to an Ubuntu Pro subscription 1 time\(s\).
      The failure was due to: an unknown error.
      The next attempt is scheduled for \d+-\d+-\d+T\d+:\d+:00.*.
      You can try manually with `sudo pro auto-attach`.
      """
    When I run `pro status` with sudo
    Then stdout matches regexp:
      """
      NOTICES
      Failed to automatically attach to an Ubuntu Pro subscription 1 time\(s\).
      The failure was due to: an unknown error.
      The next attempt is scheduled for \d+-\d+-\d+T\d+:\d+:00.*.
      You can try manually with `sudo pro auto-attach`.
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |
