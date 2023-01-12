# How to configure a timer job

All timer jobs can be configured through the `pro config set` command.
We will show how you can properly use this command to interact with timer jobs.

## Check a timer job's configuration

To see each job’s running interval, use the `show` command:

```console
$ sudo pro config show
```

You should see output which includes the timer jobs:

```
update_messaging_timer  21600
metering_timer          14400
```

## Change a timer job interval

Each job has a configuration option of the form `<job_name>_timer`,
which can be set with `pro config`. The expected value is a positive
integer for the number of seconds in the interval. For example, to
change the `update_messaging job` timer interval to run every 24 hours, run:

```console
$ sudo pro config set update_messaging_timer=86400
```

## Disable a timer job

To disable a job, set its interval to zero. For instance, to disable
the `update_messaging`  job, run:

```console
$ sudo pro config set update_messaging_timer=0
```
