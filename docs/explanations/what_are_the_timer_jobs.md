# Timer jobs

UA client sets up a systemd timer to run jobs that need to be executed recurrently. Everytime the
timer runs, it decides which jobs need to be executed based on their intervals. When a job runs
successfully, its next run is determined by the interval defined for that job.

## Current jobs

The jobs that UA client runs periodically are:

| Job | Description | Interval |
| --- | ----------- | -------- |
| update_messaging | Update MOTD and APT messages | 6 hours |
| update_status | Update UA status | 12 hours |
| metering | (Only when attached to UA services) Pings Canonical servers for contract metering | 4 hours |

- The `update_messaging` job makes sure that the MOTD and APT messages match the
available/enabled services on the system, showing information about available
packages or security updates.
- The `update_status` job makes sure the `ua status` command will have the latest
information even when executed by a non-root user, updating the
`/var/lib/ubuntu-advantage/status.json` file.
- The `metering` will inform Canonical on which services are enabled on the machine.
