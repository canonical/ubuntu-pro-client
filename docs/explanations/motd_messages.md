# Ubuntu Pro-related MOTD messages

When the Ubuntu Pro Client (`pro`) is installed on the system, it delivers
custom messages on ["Message of the Day" (MOTD)](https://wiki.debian.org/motd).
Those messages are generated directly by three different sources.

* MOTD about available updates
* MOTD about important subscription conditions
* MOTD about ESM being available

## MOTD about available updates

The [update-notifier](https://wiki.ubuntu.com/UpdateNotifier) delivers a script
via the `update-notifier-common` package called
`/usr/lib/update-notifier/apt_check.py.
With regards to Ubuntu Pro, this script is responsible for:

* Informing the user about the status of one of the ESM services; `esm-apps` if
  the machine is an LTS series, or `esm-infra` if the series is in ESM mode.
* Showing the number of `esm-infra` or `esm-apps` packages that can be upgraded
  on the machine.

`update-notifier` has always added information about potential updates to
MOTD to raise user awareness. With the advent of Ubuntu Pro they are
just more differentiated.

Note that if you run `apt_check.py` directly it might give you rather
unreadable output as it is meant for program use. You can add `--human-readable`
to see the information as it would be presented in MOTD.

### Machine is unattached

On a machine that runs an Ubuntu release for which the `esm-apps` service
is available, but not yet attached to an Ubuntu Pro subscription, there will
be a message notifying the user that there may be more security updates
available through ESM Apps.

```
Expanded Security Maintenance for Applications is not enabled.

0 updates can be applied immediately.

Enable ESM Apps to receive additional future security updates.
See https://ubuntu.com/esm or run: sudo pro status
```

### Machine is fully attached

In the opposite situation, if an LTS machine has the `esm-infra` and `esm-apps` services enabled then users will see the following output in MOTD:

```
Expanded Security Maintenance for Applications is enabled.

11 updates can be applied immediately.
5 of these updates are ESM Apps security updates.
1 of these updates is a ESM Infra security update.
5 of these updates are standard security updates.
To see these additional updates run: apt list --upgradable
```

### Machine is fully attached, on an older release

Above you have seen examples of recent (as in "still in their first 5
years of support") ubuntu releases, where the hint is about ESM Apps
extending the coverage to the universe repositories.

However, if running on an Ubuntu release that has is already past the initial
5 years of support and has thereby entered Expanded Security Maintenance
(["ESM"](https://ubuntu.com/security/esm)), we would instead see
`esm-infra` (which provides coverage for another 5 years) being shown:

```
Expanded Security Maintenance Infrastructure is enabled.

11 updates can be applied immediately.
5 of these updates are ESM Apps security updates.
1 of these updates is a ESM Infra security update.
5 of these updates are standard security updates.
To see these additional updates run: apt list --upgradable
```

### Partial service enablement

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

## MOTD about important subscription conditions

One of the [timer jobs](https://canonical-ubuntu-pro-client.readthedocs-hosted.com/en/latest/explanations/what_are_the_timer_jobs.html)
Ubuntu Pro uses can insert additional messages into MOTD.
These messages will be always delivered close to the content created by
the `update-notifier`. These additional messages are generated when `pro`
detects that certain conditions on the machine have been met. They are:

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

## MOTD about ESM being available

When Ubuntu Pro became generally available, a temporary announcement was made
through MOTD. This was intended to raise awareness of Pro now being available
and free for personal use, and was shown on systems that could be covered
by `esm-apps`.
It looked like:

```
 * Introducing Expanded Security Maintenance for Applications.
   Receive updates to over 25,000 software packages with your
   Ubuntu Pro subscription. Free for personal use.

     https://ubuntu.com/pro
```

Since this message was intended as a limited-time announcement to coincide
with the release of Ubuntu Pro into general availability, it was removed in
27.14.

## How are these messages inserted into MOTD and how can I disable them?

Just as there are different purposes to the messages outlined above,
there are different sources producing these MOTD elements that one
sees at login.

Those messages are considered important to ensure user awareness about
the free additional security coverage provided by Ubuntu Pro and about
not-yet-applied potential updates in general. Therefore it is generally not
recommended to disable them. But still, you can selectively disable them
by removing the config files that add them, as outlined below.

Removing those files is considered a conffile change to customize a program
and they will stay removed even on future upgrades or re-installations of the
related packages.

If you realize that you actually need them back you need
to reinstall the related packages and tell apt/dpkg to offer you to restore
those files via:

```
sudo apt install --reinstall -o Dpkg::Options::="--force-confask" ubuntu-advantage-tools update-notifier-common
```

## Source: MOTD about available updates

1. `update-notifier-common` has a hook `/etc/apt/apt.conf.d/99update-notifier` that runs after `apt update`.
2. That hook will update the information in `/var/lib/update-notifier/updates-available` matching the new package information that was just fetched by using `/usr/lib/update-notifier/apt-check --human-readable`.
3. At MOTD generation time, the script located at `/etc/update-motd.d/90-updates-available` checks if `/var/lib/update-notifier/updates-available` exists and if it does, inserts the message into the full MOTD.

If you want to disable any message of update-notifier (not just related to Ubuntu Pro and ESM) about potentially available updates remove `/etc/update-motd.d/90-updates-available`.

## Source: MOTD about important subscription conditions

1. The subscription status is checked periodically in the background when the machine is attached to an Ubuntu Pro subscription.
2. If one of the above conditions applies to the subscription that the machine is attached to (there are no messages generated by this for unattached machines), then the message is stored in `/var/lib/ubuntu-advantage/messages/motd-contract-status`.
3. At MOTD generation time, the script located at `/etc/update-motd.d/91-contract-ua-esm-status` checks if `/var/lib/ubuntu-advantage/messages/motd-contract-status` exists and if it does, inserts the message into the full MOTD.

If you want to disable any message about important conditions of your attached subscription remove `/etc/update-motd.d/91-contract-ua-esm-status`.

## Source: MOTD about ESM being available

1. `pro` checks regularly if a system would have `esm-apps` available to it and if so places a message in `/var/lib/ubuntu-advantage/messages/motd-esm-announce`.
2. At MOTD generation time, the script located at `/etc/update-motd.d/88-esm-announce` checks if `/var/lib/ubuntu-advantage/messages/motd-esm-announce` exists and if it does, inserts the message into the full MOTD.

If you want to disable the ESM announcement remove `/etc/update-motd.d/88-esm-announce` (or upgrade to 27.14 or later which will remove it for you).
