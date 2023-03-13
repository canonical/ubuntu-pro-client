# How to interpret the output of unattended-upgrades

On Pro Client version 27.14~, we introduced the `u.pro.unattended_upgrades.status.v1` endpoint.
This endpoint is designed to provide users with an overview of the configuration and setup for
unattended-upgrades on the machine. The expected output follows this JSON example:

```json
{
  "_schema_version": "v1",
  "data": {
    "attributes": {
      "apt_periodic_job_enabled": true,
      "package_lists_refresh_frequency_days": 1,
      "systemd_apt_timer_enabled": true,
      "unattended_upgrades_allowed_origins": [
        "${distro_id}:${distro_codename}",
        "${distro_id}:${distro_codename}-security",
        "${distro_id}ESMApps:${distro_codename}-apps-security",
        "${distro_id}ESM:${distro_codename}-infra-security"
      ],
      "unattended_upgrades_disabled_reason": null,
      "unattended_upgrades_frequency_days": 1,
      "unattended_upgrades_last_run": null,
      "unattended_upgrades_running": true
    },
    "meta": {
      "environment_vars": [],
      "raw_config": {
        "APT::Periodic::Enable": "1",
        "APT::Periodic::Unattended-Upgrade": "1",
        "APT::Periodic::Update-Package-Lists": "1",
        "Unattended-Upgrade::Allowed-Origins": [
          "${distro_id}:${distro_codename}",
          "${distro_id}:${distro_codename}-security",
          "${distro_id}ESMApps:${distro_codename}-apps-security",
          "${distro_id}ESM:${distro_codename}-infra-security"
        ]
      }
    },
    "type": "UnattendedUpgradesStatus"
  },
  "errors": [],
  "result": "success",
  "version": "27.14~16.04.1",
  "warnings": []
}
```

As we can see from this output, we have a variable named `unattended_upgrades_running`. That variable
indicates if unattended-upgrades is properly configured and running on the machine.
The value of this field will only be `true` if *ALL*  of the following prerequisites are also true:

* *`apt_periodic_job_enable` is true*: That variable indicates if the APT::Periodic::Enable configuration variable
  is turned on. If it is turned off, unattended-upgrades will not automatically run on the machine.
* *`package_lists_refresh_frequency_days` is non-zero*: That variable shows the value of APT::Periodic::Package-List-Frequency.
  This configuration defines the daily frequency for updating package sources in the background. If it has a zero value, this step will never
  happen and unattended-upgrades might not be able to install new versions of the packages.
* *`systemd_apt_timer_enabled` is true*: This variable is true if both `apt-daily.timer` and `apt-daily-upgrade.timer` are running
  on the machine. These timers are the ones that control when unattended-upgrades run. The first job, `apt-daily.timer` is responsible
  for triggering the code that downloads the lastest package information on the system. The second job, `apt-daily-upgrade.timer` is
  responsible for running unattended-upgrades to download the latest version of the packages. If one of these jobs is disabled,
  unattended-upgrades might not work as expected.
* *`unattended_upgrades_allowed_origins` is not empty*: This variable defines the origins that
  unattended-upgrades can use to install a package. If that list is empty, no packages can be
  installed and unattended-upgrades will not work as expected.
* *`unattended_upgrades_frequency_days` is non-zero*: That variable shows the value of
  APT::Periodic::Unattended-Upgrade. This configuration defines the daily frequency for running
  unattended-upgrades in the background. Therefore, if it has a zero value, the command will never
  run.


If any of those conditions are not met, the variable
*unattended_upgrades_disabled_reason* will contain an object explaining why unattended-upgrades is
not running. For example, if `package_lists_refresh_frequency_days` has a zero value, we will see
the following value for *unattended_upgrades_disabled_reason*:

```json
{
    "msg": "APT::Periodic::Update-Package-Lists is turned off",
    "code": "unattended-upgrades-cfg-value-turned-off"
}
```
