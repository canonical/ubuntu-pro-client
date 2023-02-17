Feature: api.u.unattended_upgrades.status.v1

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: v1 unattended upgrades status
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `pro api u.unattended_upgrades.status.v1` as non-root
        Then stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"apt_periodic_job_enabled": true, "package_lists_refresh_frequency_days": 1, "systemd_apt_timer_enabled": true, "unattended_upgrades_allowed_origins": \["\$\{distro_id\}:\$\{distro_codename\}", "\$\{distro_id\}:\$\{distro_codename\}\-security", "\$\{distro_id\}ESMApps:\$\{distro_codename\}\-apps-security", "\$\{distro_id\}ESM:\$\{distro_codename\}\-infra-security"\], "unattended_upgrades_disabled_reason": null, "unattended_upgrades_frequency_days": 1, "unattended_upgrades_last_run": null, "unattended_upgrades_running": true}, "meta": {"environment_vars": \[\], "raw_config": {"APT::Periodic::Enable": "1", "APT::Periodic::Unattended-Upgrade": "1", "APT::Periodic::Update-Package-Lists": "1", "Unattended-Upgrade::Allowed-Origins": \["\$\{distro_id\}:\$\{distro_codename\}", "\$\{distro_id\}:\$\{distro_codename\}\-security", "\$\{distro_id\}ESMApps:\$\{distro_codename\}\-apps-security", "\$\{distro_id\}ESM:\$\{distro_codename\}\-infra-security"\][,]?\s*<extra_field>}}, "type": "UnattendedUpgradesStatus"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I create the file `/etc/apt/apt.conf.d/99test` with the following:
        """
        APT::Periodic::Enable "0";
        """
        And I run `apt-get update` with sudo
        And I run `apt-get install jq -y` with sudo
        And I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.apt_periodic_job_enabled` as non-root
        Then I will see the following on stdout:
        """
        false
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.unattended_upgrades_running` as non-root
        Then I will see the following on stdout:
        """
        false
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.unattended_upgrades_disabled_reason.msg` as non-root
        Then I will see the following on stdout:
        """
        "APT::Periodic::Enable is turned off"
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.unattended_upgrades_disabled_reason.code` as non-root
        Then I will see the following on stdout:
        """
        "unattended-upgrades-cfg-value-turned-off"
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq '.data.meta.raw_config.\"APT::Periodic::Enable\"'` as non-root
        Then I will see the following on stdout:
        """
        "0"
        """
        When I create the file `/etc/apt/apt.conf.d/99test` with the following:
        """
        APT::Periodic::Update-Package-Lists "0";
        """
        And I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.apt_periodic_job_enabled` as non-root
        Then I will see the following on stdout:
        """
        true
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.package_lists_refresh_frequency_days` as non-root
        Then I will see the following on stdout:
        """
        0
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.unattended_upgrades_running` as non-root
        Then I will see the following on stdout:
        """
        false
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.unattended_upgrades_disabled_reason.msg` as non-root
        Then I will see the following on stdout:
        """
        "APT::Periodic::Update-Package-Lists is turned off"
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.unattended_upgrades_disabled_reason.code` as non-root
        Then I will see the following on stdout:
        """
        "unattended-upgrades-cfg-value-turned-off"
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq '.data.meta.raw_config.\"APT::Periodic::Update-Package-Lists\"'` as non-root
        Then I will see the following on stdout:
        """
        "0"
        """
        When I create the file `/etc/apt/apt.conf.d/99test` with the following:
        """
        APT::Periodic::Unattended-Upgrade "0";
        """
        And I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.unattended_upgrades_frequency_days` as non-root
        Then I will see the following on stdout:
        """
        0
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.package_lists_refresh_frequency_days` as non-root
        Then I will see the following on stdout:
        """
        1
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.unattended_upgrades_running` as non-root
        Then I will see the following on stdout:
        """
        false
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.unattended_upgrades_disabled_reason.msg` as non-root
        Then I will see the following on stdout:
        """
        "APT::Periodic::Unattended-Upgrade is turned off"
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.unattended_upgrades_disabled_reason.code` as non-root
        Then I will see the following on stdout:
        """
        "unattended-upgrades-cfg-value-turned-off"
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq '.data.meta.raw_config.\"APT::Periodic::Unattended-Upgrade\"'` as non-root
        Then I will see the following on stdout:
        """
        "0"
        """
        When I run `systemctl stop apt-daily.timer` with sudo
        And I run `rm /etc/apt/apt.conf.d/99test` with sudo
        And I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.systemd_apt_timer_enabled` as non-root
        Then I will see the following on stdout:
        """
        false
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.unattended_upgrades_running` as non-root
        Then I will see the following on stdout:
        """
        false
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.unattended_upgrades_disabled_reason.msg` as non-root
        Then I will see the following on stdout:
        """
        "apt-daily.timer jobs are not running"
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.unattended_upgrades_disabled_reason.code` as non-root
        Then I will see the following on stdout:
        """
        "unattended-upgrades-systemd-job-disabled"
        """
        When I create the file `/etc/apt/apt.conf.d/50unattended-upgrades` with the following:
        """
        APT::Periodic::Unattended-Upgrade "1";
        """
        And I run `systemctl start apt-daily.timer` with sudo
        And I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.unattended_upgrades_frequency_days` as non-root
        Then I will see the following on stdout:
        """
        1
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.systemd_apt_timer_enabled` as non-root
        Then I will see the following on stdout:
        """
        true
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.unattended_upgrades_allowed_origins` as non-root
        Then I will see the following on stdout:
        """
        []
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.unattended_upgrades_running` as non-root
        Then I will see the following on stdout:
        """
        false
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.unattended_upgrades_disabled_reason.msg` as non-root
        Then I will see the following on stdout:
        """
        "Unattended-Upgrade::Allowed-Origins is empty"
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.unattended_upgrades_disabled_reason.code` as non-root
        Then I will see the following on stdout:
        """
        "unattended-upgrades-cfg-list-value-empty"
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq '.data.meta.raw_config.\"Unattended-Upgrade::Allowed-Origins\"'` as non-root
        Then I will see the following on stdout:
        """
        null
        """
        When I run `/usr/lib/apt/apt.systemd.daily update` with sudo
        And I run `/usr/lib/apt/apt.systemd.daily install` with sudo
        And I run shell command `pro api u.unattended_upgrades.status.v1 | jq .data.attributes.unattended_upgrades_last_run` as non-root
        Then stdout matches regexp:
        """
        "(?!null).*"
        """
        When I create the file `/etc/apt/apt.conf.d/99test` with the following:
        """
        Unattended-Upgrade::Mail "mail";
        Unattended-Upgrade::Package-Blacklist {
            "vim";
        };
        """
        And I run shell command `pro api u.unattended_upgrades.status.v1 | jq '.data.meta.raw_config.\"Unattended-Upgrade::Mail\"'` as non-root
        Then I will see the following on stdout:
        """
        "mail"
        """
        When I run shell command `pro api u.unattended_upgrades.status.v1 | jq '.data.meta.raw_config.\"Unattended-Upgrade::Package-Blacklist\"'` as non-root
        Then I will see the following on stdout:
        """
        [
          "vim"
        ]
        """

        Examples: ubuntu release
           | release | extra_field                               |
           | xenial  |                                           |
           | bionic  | "Unattended-Upgrade::DevRelease": "false" |
           | focal   | "Unattended-Upgrade::DevRelease": "auto"  |
           | jammy   | "Unattended-Upgrade::DevRelease": "auto"  |
           | kinetic | "Unattended-Upgrade::DevRelease": "auto"  |
           | lunar   | "Unattended-Upgrade::DevRelease": "auto"  |
