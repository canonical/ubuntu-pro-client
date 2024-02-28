Feature: auto-attach retries periodically on failures

  Scenario Outline: auto-attach retries for a month and updates status
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I change contract to staging with sudo
    When I install ubuntu-advantage-pro
    When I reboot the machine
    When I verify that running `systemctl status ua-auto-attach.service` `as non-root` exits `3`
    Then stdout matches regexp:
      """
      Active: failed
      """
    Then stdout matches regexp:
      """
      creating flag file to trigger retries
      """
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
      The failure was due to: Canonical servers did not recognize this machine as Ubuntu Pro: ".*".
      The next attempt is scheduled for \d+-\d+-\d+T\d+:\d+:00.*.
      You can try manually with `sudo pro auto-attach`.
      """
    When I run `pro status` with sudo
    Then stdout matches regexp:
      """
      NOTICES
      Failed to automatically attach to an Ubuntu Pro subscription 1 time\(s\).
      The failure was due to: Canonical servers did not recognize this machine as Ubuntu Pro: ".*".
      The next attempt is scheduled for \d+-\d+-\d+T\d+:\d+:00.*.
      You can try manually with `sudo pro auto-attach`.
      """
    # simulate a middle attempt with different reason
    When I set `interval_index` = `10` in json file `/var/lib/ubuntu-advantage/retry-auto-attach-state.json`
    When I set `failure_reason` = `"an unknown error"` in json file `/var/lib/ubuntu-advantage/retry-auto-attach-state.json`
    When I run `systemctl restart ubuntu-advantage.service` with sudo
    And I wait `5` seconds
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
      Failed to automatically attach to an Ubuntu Pro subscription 11 time\(s\).
      The failure was due to: an unknown error.
      The next attempt is scheduled for \d+-\d+-\d+T\d+:\d+:00.*.
      You can try manually with `sudo pro auto-attach`.
      """
    When I run `pro status` with sudo
    Then stdout matches regexp:
      """
      NOTICES
      Failed to automatically attach to an Ubuntu Pro subscription 11 time\(s\).
      The failure was due to: an unknown error.
      The next attempt is scheduled for \d+-\d+-\d+T\d+:\d+:00.*.
      You can try manually with `sudo pro auto-attach`.
      """
    # simulate all attempts failing
    When I set `interval_index` = `18` in json file `/var/lib/ubuntu-advantage/retry-auto-attach-state.json`
    When I run `systemctl restart ubuntu-advantage.service` with sudo
    And I wait `5` seconds
    Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `3`
    Then stdout contains substring
      """
      Active: inactive (dead)
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
      Failed to automatically attach to an Ubuntu Pro subscription 19 time\(s\).
      The most recent failure was due to: an unknown error.
      Try re-launching the instance or report this issue by running `ubuntu-bug ubuntu-advantage-tools`
      You can try manually with `sudo pro auto-attach`.
      """
    When I run `pro status` with sudo
    Then stdout matches regexp:
      """
      NOTICES
      Failed to automatically attach to an Ubuntu Pro subscription 19 time\(s\).
      The most recent failure was due to: an unknown error.
      Try re-launching the instance or report this issue by running `ubuntu-bug ubuntu-advantage-tools`
      You can try manually with `sudo pro auto-attach`.
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | aws.generic   |
      | xenial  | azure.generic |
      | xenial  | gcp.generic   |
      | bionic  | aws.generic   |
      | bionic  | azure.generic |
      | bionic  | gcp.generic   |
      | focal   | aws.generic   |
      | focal   | azure.generic |
      | focal   | gcp.generic   |
      | jammy   | aws.generic   |
      | jammy   | azure.generic |
      | jammy   | gcp.generic   |

  Scenario Outline: auto-attach retries stop if manual auto-attach succeeds
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
      """
      contract_url: 'https://contracts.canonical.com'
      data_dir: /var/lib/ubuntu-advantage
      log_level: debug
      log_file: /var/log/ubuntu-advantage.log
      """
    When I create the file `/var/lib/ubuntu-advantage/response-overlay.json` with the following:
      """
      {
          "https://contracts.canonical.com/v1/clouds/$behave_var{cloud system-under-test}/token": [{
            "type": "contract",
            "code": 400,
            "response": {
              "message": "error"
            }
          }]
      }
      """
    And I append the following on uaclient config:
      """
      features:
        serviceclient_url_responses: "/var/lib/ubuntu-advantage/response-overlay.json"
      """
    When I reboot the machine
    When I verify that running `systemctl status ua-auto-attach.service` `as non-root` exits `3`
    Then stdout matches regexp:
      """
      Active: failed
      """
    Then I verify that running `systemctl status ubuntu-advantage.service` `with sudo` exits `0`
    Then stdout matches regexp:
      """
      Active: active \(running\)
      """
    When I run `run-parts /etc/update-motd.d/` with sudo
    Then stdout matches regexp:
      """
      Failed to automatically attach to an Ubuntu Pro subscription
      """
    When I run `pro status` with sudo
    Then stdout matches regexp:
      """
      NOTICES
      Failed to automatically attach to an Ubuntu Pro subscription
      """
    When I append the following on uaclient config:
      """
      features: {}
      """
    # The retry service waits 15 minutes before trying again, so this
    # _should_ run and finish before the retry service has done anything
    When I run `pro auto-attach` with sudo
    When I verify that running `systemctl status ubuntu-advantage.service` `as non-root` exits `3`
    Then stdout contains substring
      """
      Active: inactive (dead)
      """
    # Workaround for livepatch issue LP #2015585
    Then I verify that running `run-parts /etc/update-motd.d/` `with sudo` exits `0,1`
    Then stdout does not match regexp:
      """
      Failed to automatically attach to an Ubuntu Pro subscription
      """
    When I run `pro status` with sudo
    Then stdout does not match regexp:
      """
      NOTICES
      Failed to automatically attach to an Ubuntu Pro subscription
      """

    Examples: ubuntu release
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

  Scenario Outline: gcp auto-detect triggers retries on fail
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
      """
      contract_url: 'https://contracts.canonical.com'
      data_dir: /var/lib/ubuntu-advantage
      log_level: debug
      log_file: /var/log/ubuntu-advantage.log
      """
    When I create the file `/var/lib/ubuntu-advantage/response-overlay.json` with the following:
      """
      {
          "https://contracts.canonical.com/v1/clouds/gcp/token": [{
            "type": "contract",
            "code": 400,
            "response": {
              "message": "error"
            }
          }]
      }
      """
    And I append the following on uaclient config:
      """
      features:
        serviceclient_url_responses: "/var/lib/ubuntu-advantage/response-overlay.json"
      """
    When I run `systemctl start ubuntu-advantage.service` with sudo
    When I wait `1` seconds
    When I verify that running `systemctl status ubuntu-advantage.service` `as non-root` exits `0`
    Then stdout contains substring
      """
      Active: active (running)
      """
    Then stdout matches regexp:
      """
      mode: poll for pro license
      """
    Then stdout matches regexp:
      """
      creating flag file to trigger retries
      """
    Then stdout matches regexp:
      """
      mode: retry auto attach
      """
    When I run `run-parts /etc/update-motd.d/` with sudo
    Then stdout matches regexp:
      """
      Failed to automatically attach to an Ubuntu Pro subscription
      """
    When I run `pro status` with sudo
    Then stdout matches regexp:
      """
      NOTICES
      Failed to automatically attach to an Ubuntu Pro subscription
      """

    Examples: ubuntu release
      | release | machine_type |
      | xenial  | gcp.pro      |
      | bionic  | gcp.pro      |
      | focal   | gcp.pro      |
      | jammy   | gcp.pro      |

  Scenario Outline: auto-attach retries eventually succeed and clean up
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    # modify the wait time to be shorter so we don't have to wait 15m
    When I replace `900,  # 15m (T+15m)` in `/usr/lib/python3/dist-packages/uaclient/daemon/retry_auto_attach.py` with `60,`
    When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
      """
      contract_url: 'https://contracts.canonical.com'
      data_dir: /var/lib/ubuntu-advantage
      log_level: debug
      log_file: /var/log/ubuntu-advantage.log
      """
    When I create the file `/var/lib/ubuntu-advantage/response-overlay.json` with the following:
      """
      {
          "https://contracts.canonical.com/v1/clouds/$behave_var{cloud system-under-test}/token": [{
            "type": "contract",
            "code": 400,
            "response": {
              "message": "error"
            }
          }]
      }
      """
    And I append the following on uaclient config:
      """
      features:
        serviceclient_url_responses: "/var/lib/ubuntu-advantage/response-overlay.json"
      """
    When I reboot the machine
    When I verify that running `systemctl status ua-auto-attach.service` `as non-root` exits `3`
    Then stdout matches regexp:
      """
      Active: failed
      """
    When I verify that running `systemctl status ubuntu-advantage.service` `as non-root` exits `0`
    Then stdout matches regexp:
      """
      Active: active \(running\)
      """
    When I run `run-parts /etc/update-motd.d/` with sudo
    Then stdout matches regexp:
      """
      Failed to automatically attach to an Ubuntu Pro subscription
      """
    When I run `pro status` with sudo
    Then stdout matches regexp:
      """
      NOTICES
      Failed to automatically attach to an Ubuntu Pro subscription
      """
    When I append the following on uaclient config:
      """
      features: {}
      """
    When I wait `60` seconds
    And I run `pro status --wait` with sudo
    Then the machine is attached
    When I verify that running `systemctl status ubuntu-advantage.service` `as non-root` exits `3`
    Then stdout contains substring
      """
      Active: inactive (dead)
      """
    # Workaround for livepatch issue LP #2015585
    Then I verify that running `run-parts /etc/update-motd.d/` `with sudo` exits `0,1`
    Then stdout does not match regexp:
      """
      Failed to automatically attach to an Ubuntu Pro subscription
      """
    When I run `pro status` with sudo
    Then stdout does not match regexp:
      """
      NOTICES
      Failed to automatically attach to an Ubuntu Pro subscription
      """

    Examples: ubuntu release
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
