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

### Advertising `esm-apps` service

When we detect that `esm-apps` is supported and not enabled on the system, we
advertise it using the following message that is delivered before the
`update-notifier` message:

```
* Introducing Expanded Security Maintenance for Applications.
  Receive updates to over 25,000 software packages with your
  Ubuntu Pro subscription. Free for personal use

    https://ubuntu.com/16-04 
```

```{note}
Note that we could also advertise the `esm-infra` service instead. This will
happen if you use an ESM release. Additionally, the the URL we use to advertise
the service is different based on the series that is running on the machine.

Additionally, all of those Ubuntu Pro custom messages are delivered into
`/var/lib/ubuntu-advantage/messages`. We also add custom scripts into
`/etc/update-motd.d` to check if those messages exist and if they do, insert
them into the full MOTD message.
```
