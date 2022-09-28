# How to collect Ubuntu Pro Client logs

To collect all of the necessary logs for Ubuntu Pro Client (`pro`), please run the command:

```console
$ sudo pro collect-logs
```

This command creates a tarball with all relevant data for debugging possible problems with `pro`.
It puts together:
* The Ubuntu Pro Client configuration file (the default is `/etc/ubuntu-advantage/uaclient.conf`)
* The Ubuntu Pro Client log files (the default is `/var/log/ubuntu-advantage*`)
* The files in `/etc/apt/sources.list.d/*` related to UA
* Output of `systemctl status` for the Ubuntu Pro Client related services
* Status of the timer jobs, `canonical-livepatch`, and the systemd timers
* Output of `cloud-id`, `dmesg` and `journalctl`

Sensitive data is redacted from all files included in the tarball. As of now, the command must be run as root.

Running the command creates a `ua_logs.tar.gz` file in the current directory.
The output file path/name can be changed using the `-o` option.
