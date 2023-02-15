# Ubuntu Pro-related APT messages

When running some APT commands, you might see Ubuntu Pro-related messages in
the output of those commands. Currently, we deliver those messages when
running either `apt upgrade` or `apt dist-upgrade`. The scenarios
where we deliver those messages are:

## ESM series with esm-infra service disabled

When you run `apt upgrade` on an ESM release, like Xenial, we advertise
the `esm-infra` service if packages could be upgraded by enabling the service:

```
Reading package lists... Done
Building dependency tree
Reading state information... Done
Calculating upgrade... Done
The following package was automatically installed and is no longer required:
  libfreetype6
  Use 'apt autoremove' to remove it.
The following security updates require Ubuntu Pro with 'esm-infra' enabled:
  libpam0g libpam-modules openssl ntfs-3g git-man libsystemd0 squashfs-tools git openssh-sftp-server udev libpam-runtime isc-dhcp-common libx11-6 libudev1 apport python3-apport systemd-sysv liblz4-1 libpam-systemd systemd libpam-modules-bin openssh-server libx11-data openssh-client libxml2 curl isc-dhcp-client python3-problem-report libcurl3-gnutls libssl1.0.0
Learn more about Ubuntu Pro for 16.04 at https://ubuntu.com/16-04
```

## LTS series with esm-apps service disabled

When you are running `apt upgraded` on a LTS release, like Focal, we advertise
the `esm-apps` service if packages could be upgraded by enabling the service:

```
Reading package lists... Done
Building dependency tree
Reading state information... Done
Calculating upgrade... Done
The following package was automatically installed and is no longer required:
  libfreetype6
Use 'apt autoremove' to remove it.
Get more security updates through Ubuntu Pro with 'esm-apps' enabled:
  adminer editorconfig ansible
Learn more about Ubuntu Pro at https://ubuntu.com/pro
0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
```

## ESM package count

If both ESM services are enabled on the system, we deliver a package count
related to each service near the end of the `apt` command:

```
1 standard LTS security update, 29 esm-infra security updates and 8 esm-apps security updates
```

We only deliver this message if the service is enabled *and* we upgraded
packages related to it. For example, if we had no `esm-infra` package upgrades,
the message would be:

```
1 standard LTS security update and 8 esm-apps security updates
```

## Expired contract

If we detect that your contract is expired, we will deliver the following
message advertising `esm-infra` in the middle of the `apt upgrade` command:

```
#
# *Your Ubuntu Pro subscription has EXPIRED*
# 10 additional security update(s) require Ubuntu Pro with '{service}' enabled.
# Renew your service at https://ubuntu.com/pro
#
```
 
If we don't have any `esm-infra`-related packages to upgrade, we would show the
following message instead:

```
#
# *Your Ubuntu Pro subscription has EXPIRED*
# Renew your service at https://ubuntu.com/pro
#
```

## Contract is about to expire

Similarly, if we detect that your contract is about to expire, we deliver the
following message in the middle of the `apt` command:

```
#
# CAUTION: Your Ubuntu Pro subscription will expire in 2 days.
# Renew your subscription at https://ubuntu.com/pro to ensure continued
# security coverage for your applications.
#
```

## Contract has expired, but still in grace period

Additionally, if we detect that the contract has expired, but is still in the
grace period, the following message will be seen in the middle of the `apt`
command output:

```
#
# CAUTION: Your Ubuntu Pro subscription expired on 10 Sep 2021.
# Renew your subscription at https://ubuntu.com/pro to ensure continued
# security coverage for your applications.
# Your grace period will expire in 11 days.
#
```

## How are the APT messages generated?

We have two distinct `apt` hooks that allow us to deliver these messages when
you run `apt upgrade` or `apt dist-upgrade`. They are:

### `apt-esm-hook`

Responsible for populating templates with accurate package counts (i.e. the package
count we see on the Expired contract messages).
However, the messaging here is created by two distinct steps:

1. Our [update_messages](what_are_the_timer_jobs.md) timer job creates
   templates for the APT messages this hook will deliver. We cannot create the
   full message on the timer job, because we need the accurate package names
   and count. This information can only be obtained when running the `apt`
   command.

   ```{note}
   These templates will only be produced if certain conditions are met. For
   example, we only produce "expired contract" templates if the contracts are
   indeed expired.
   ```

2. When you run either `apt upgrade` or `apt dist-upgrade`, the hook
   searches for these templates and if they exist, they are populated with the
   correct `apt` content and delivered to the user.

### `apt-esm-json-hook`

The JSON hook is responsible for delivering the rest of the message we have presented here.
This hook is used to inject the message in the exact place we want, so we need to use a specific `apt`
[JSON hook](https://salsa.debian.org/apt-team/apt/-/blob/main/doc/json-hooks-protocol.md)
to communicate with it.

```{note}
Those hooks are only delivered on LTS releases. This is because the hooks will
not deliver useful messages on non-LTS due to lack of support for ESM services.
```

## How are APT configured to deliver those messages?

We currently ship the package the `20apt-esm-hook.conf` configuration that
configures both the basic apt hooks to call our `apt-esm-hook` binary, and also
the `json` API of `apt` to call our `apt-esm-json-hook` binary.
