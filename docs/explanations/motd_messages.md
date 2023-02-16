# Ubuntu Pro-related MOTD messages

When the Ubuntu Pro Client (`pro`) is installed on the system, it delivers
custom messages on ["Message of the Day" (MOTD)](https://wiki.debian.org/motd).
Those messages are generated directly by two different sources.

## Python-scripted MOTD

The [update-notifier](https://wiki.ubuntu.com/UpdateNotifier) delivers a script
called `apt_check.py`. With regards to Ubuntu Pro, this script is responsible
for:
  
* Informing the user about the status of one of the ESM services; `esm-apps` if
  the machine is an LTS series, or `esm-infra` if the series is in ESM mode.
* Showing the number of `esm-infra` or `esm-apps` packages that can be upgraded
  on the machine.

For example, here is the output of the `apt_check.py` script on a LTS machine
when both of those services are enabled:

```
Expanded Security Maintenance for Applications is enabled.

11 updates can be applied immediately.
5 of these updates are ESM Apps security updates.
1 of these updates is a ESM Infra security update.
5 of these updates are standard security updates.
To see these additional updates run: apt list --upgradable
```

However, if we were running this on an ESM series, we would instead see
`esm-infra` being advertised:

```
Expanded Security Maintenance Infrastructure is enabled.

11 updates can be applied immediately.
5 of these updates are ESM Apps security updates.
1 of these updates is a ESM Infra security update.
5 of these updates are standard security updates.
To see these additional updates run: apt list --upgradable
```

Now let's consider a scenario where one of these services is not enabled. For
example, if `esm-apps` was disabled, the output will be:

```
Expanded Security Maintenance for Applications is not enabled.
  
6 updates can be applied immediately.
1 of these updates is a ESM Infra security update.
5 of these updates are standard security updates.
To see these additional updates run: apt list --upgradable
  
5 additional security updates can be applied with ESM Apps
Learn more about enabling ESM Apps for Ubuntu 16.04 at
https://ubuntu.com/16-04
```

At the end of the output we can see the number of packages that *could* be
upgraded if that service was enabled. Note that we would deliver the same
information for `esm-infra` if the service was disabled and the series running
on the machine is in ESM state.

## MOTD through Ubuntu Pro timer jobs

One of the timer jobs Ubuntu Pro uses can insert additional messages into MOTD.
These messages will be always delivered before or after the content created by
the Python script delivered by `update-notifier`. These additional messages are
generated when `pro` detects that certain conditions on the machine have been
met. They are:

### Subscription expired

When the Ubuntu Pro subscription is expired, `pro` will deliver the following
message after the `update-notifier` message:

```
*Your Ubuntu Pro subscription has EXPIRED*
2 additional security update(s) require Ubuntu Pro with 'esm-infra' enabled.
Renew your service at https://ubuntu.com/pro
```

### Subscription about to expire

When the Ubuntu Pro subscription is about to expire, we deliver the following
message after the `update-notifier` message:

```
CAUTION: Your Ubuntu Pro subscription will expire in 2 days.
Renew your subscription at https://ubuntu.com/pro to ensure continued security
coverage for your applications.
```

### Subscription expired but within grace period

When the Ubuntu Pro subscription has expired, but is still within the grace
period, we deliver the following message after the `update-notifier` script:

```
CAUTION: Your Ubuntu Pro subscription expired on 10 Sep 2021.
Renew your subscription at https://ubuntu.com/pro to ensure continued security
coverage for your applications.
Your grace period will expire in 9 days.
```

### How are these messages updated and inserted into MOTD?

1. The contract status is checked periodically in the background when the machine is attached to an Ubuntu Pro contract.
2. If one of the above messages applies to the contract that the machine is attached to, then the message is stored in `/var/lib/ubuntu-advantage/messages/motd-contract-status`.
3. At MOTD generation time, the script located at `/etc/update-motd.d/91-contract-ua-esm-status` checks if `/var/lib/ubuntu-advantage/messages/motd-contract-status` exists and if it does, inserts the message into the full MOTD.
