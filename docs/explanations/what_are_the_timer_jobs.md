# Timer jobs explained

Ubuntu Pro Client (`pro`) sets up a `systemd` timer to run jobs that need to be
carried out periodically. Every time the timer runs, it decides which jobs need
to be performed based on their intervals. When a job runs successfully, its next
run is determined by the interval defined for that job.

## Current jobs

The jobs that `pro` runs periodically are `metering` and `update_messaging`.

### The `update_messaging` job

`update_messaging` updates the MOTD and APT messages every 6 hours. It ensures
that the MOTD and APT messages displayed on the system match those that are
available/enabled. It finds updated information about available packages or
security updates and shows these to the user. 

### The `metering` job

`metering` pings the Canonical servers for contract metering every 4 hours. It
informs Canonical which services are enabled on the machine. 

```{note}
The `metering` job only runs when attached to an Ubuntu Pro subscription.
```
