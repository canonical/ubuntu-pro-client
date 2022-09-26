Feature: api.u.pro.attach.auto.configure_retry_service

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: v1 successfully triggers retry service when run during startup
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I change contract to staging with sudo
        When I create the file `/lib/systemd/system/apitest.service` with the following
        """
        [Unit]
        Description=test
        Before=cloud-config.service
        After=cloud-config.target

        [Service]
        Type=oneshot
        ExecStart=/usr/bin/pro api u.pro.attach.auto.configure_retry_service.v1

        [Install]
        WantedBy=cloud-config.service multi-user.target
        """
        When I run `systemctl enable apitest.service` with sudo
        When I reboot the machine
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
        The failure was due to: an unknown error.
        The next attempt is scheduled for \d+-\d+-\d+T\d+:\d+:00.*.
        You can try manually with `sudo ua auto-attach`.
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        NOTICES
        Failed to automatically attach to Ubuntu Pro services 1 time\(s\).
        The failure was due to: an unknown error.
        The next attempt is scheduled for \d+-\d+-\d+T\d+:\d+:00.*.
        You can try manually with `sudo ua auto-attach`.
        """
        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | jammy   |
