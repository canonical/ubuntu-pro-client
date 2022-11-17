Feature: auto-attach retries periodically on failures

    @series.lts
    @uses.config.machine_type.aws.generic
    @uses.config.machine_type.azure.generic
    @uses.config.machine_type.gcp.generic
    Scenario Outline: auto-attach retries for a month and updates status
        Given a `<release>` machine with ubuntu-advantage-tools installed
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
        Failed to automatically attach to Ubuntu Pro services 1 time\(s\).
        The failure was due to: Canonical servers did not recognize this machine as Ubuntu Pro: ".*".
        The next attempt is scheduled for \d+-\d+-\d+T\d+:\d+:00.*.
        You can try manually with `sudo pro auto-attach`.
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        NOTICES
        Failed to automatically attach to Ubuntu Pro services 1 time\(s\).
        The failure was due to: Canonical servers did not recognize this machine as Ubuntu Pro: ".*".
        The next attempt is scheduled for \d+-\d+-\d+T\d+:\d+:00.*.
        You can try manually with `sudo pro auto-attach`.
        """

        # simulate a middle attempt with different reason
        When I set `interval_index` = `10` in json file `/var/lib/ubuntu-advantage/retry-auto-attach-state.json`
        When I set `failure_reason` = `"an unknown error"` in json file `/var/lib/ubuntu-advantage/retry-auto-attach-state.json`
        When I run `systemctl restart ubuntu-advantage.service` with sudo
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
        Failed to automatically attach to Ubuntu Pro services 11 time\(s\).
        The failure was due to: an unknown error.
        The next attempt is scheduled for \d+-\d+-\d+T\d+:\d+:00.*.
        You can try manually with `sudo pro auto-attach`.
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        NOTICES
        Failed to automatically attach to Ubuntu Pro services 11 time\(s\).
        The failure was due to: an unknown error.
        The next attempt is scheduled for \d+-\d+-\d+T\d+:\d+:00.*.
        You can try manually with `sudo pro auto-attach`.
        """

        # simulate all attempts failing
        When I set `interval_index` = `18` in json file `/var/lib/ubuntu-advantage/retry-auto-attach-state.json`
        When I run `systemctl restart ubuntu-advantage.service` with sudo
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
        Failed to automatically attach to Ubuntu Pro services 19 times.
        The most recent failure was due to: an unknown error.
        Try re-launching the instance or report this issue by running `ubuntu-bug ubuntu-advantage-tools`
        You can try manually with `sudo pro auto-attach`.
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        NOTICES
        Failed to automatically attach to Ubuntu Pro services 19 times.
        The most recent failure was due to: an unknown error.
        Try re-launching the instance or report this issue by running `ubuntu-bug ubuntu-advantage-tools`
        You can try manually with `sudo pro auto-attach`.
        """
        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | jammy   |


    @series.lts
    @uses.config.machine_type.aws.pro
    @uses.config.machine_type.azure.pro
    @uses.config.machine_type.gcp.pro
    Scenario Outline: auto-attach retries stop if manual auto-attach succeeds
        Given a `<release>` machine with ubuntu-advantage-tools installed
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
            "https://contracts.canonical.com/v1/clouds/<cloud>/token": [{
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
        Failed to automatically attach to Ubuntu Pro services
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        NOTICES
        Failed to automatically attach to Ubuntu Pro services
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
        When I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout does not match regexp:
        """
        Failed to automatically attach to Ubuntu Pro services
        """
        When I run `pro status` with sudo
        Then stdout does not match regexp:
        """
        NOTICES
        Failed to automatically attach to Ubuntu Pro services
        """
        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | jammy   |

    @series.lts
    @uses.config.machine_type.gcp.pro
    Scenario Outline: gcp auto-detect triggers retries on fail
        Given a `<release>` machine with ubuntu-advantage-tools installed
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
        Failed to automatically attach to Ubuntu Pro services
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        NOTICES
        Failed to automatically attach to Ubuntu Pro services
        """
        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | jammy   |


    @series.lts
    @uses.config.machine_type.aws.pro
    @uses.config.machine_type.azure.pro
    @uses.config.machine_type.gcp.pro
    Scenario Outline: auto-attach retries eventually succeed and clean up
        Given a `<release>` machine with ubuntu-advantage-tools installed
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
            "https://contracts.canonical.com/v1/clouds/<cloud>/token": [{
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
        Failed to automatically attach to Ubuntu Pro services
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        NOTICES
        Failed to automatically attach to Ubuntu Pro services
        """
        When I append the following on uaclient config:
        """
        features: {}
        """
        When I wait `60` seconds
        When I run `ua status --wait --format yaml` with sudo
        Then stdout contains substring
        """
        attached: true
        """
        When I verify that running `systemctl status ubuntu-advantage.service` `as non-root` exits `3`
        Then stdout contains substring
        """
        Active: inactive (dead)
        """
        When I run `run-parts /etc/update-motd.d/` with sudo
        Then stdout does not match regexp:
        """
        Failed to automatically attach to Ubuntu Pro services
        """
        When I run `pro status` with sudo
        Then stdout does not match regexp:
        """
        NOTICES
        Failed to automatically attach to Ubuntu Pro services
        """
        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | jammy   |
