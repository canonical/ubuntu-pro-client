# Timer jobs

Ubuntu Pro Client (`pro`) sets up a systemd timer to run jobs that need to be executed recurrently. Everytime the
timer runs, it decides which jobs need to be executed based on their intervals. When a job runs
successfully, its next run is determined by the interval defined for that job.

## Current jobs

The jobs that `pro` runs periodically are:

| Job | Description | Interval |
| --- | ----------- | -------- |
| update_messaging | Update MOTD and APT messages | 6 hours |
| metering | (Only when attached to Ubuntu Pro services) Pings Canonical servers for contract metering | 4 hours |

- The `update_messaging` job makes sure that the MOTD and APT messages match the
available/enabled services on the system, showing information about available
packages or security updates.
- The `metering` will inform Canonical on which services are enabled on the machine.
