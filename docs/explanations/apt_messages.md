# UA related APT messages

When running some APT commands, you might see Ubuntu Advantage (UA) related messages on
the output of those commands. Currently, we deliver those messages when
running either `apt-get upgrade` or `apt-get dist-upgrade` commands. The scenarios
where we deliver those messages are:

* **ESM series with esm-infra service disabled**: When you are running a machine
  with an ESM series, like Xenial, we advertise the `esm-infra` service if packages could
  be upgraded by enabling the service:

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

  Note that the ESM message is located in the middle of the `apt-get` command output. Additionally,
  if there are no packages to upgrade at the moment, we would instead deliver:

  ```
  Receive additional future security updates with Ubuntu Pro.
  Learn more about Ubuntu Pro for 16.04 at https://ubuntu.com/16-04
  ```

  > **Note**
  > If the user is using a LTS series instead, we will advertise `esm-apps`.

* **esm package count**: If both ESM services are enabled on the system,
  we deliver a package count related to each service near the end of the `apt-get` command:

  ```
  1 standard LTS security update, 29 esm-infra security updates and 8 esm-apps security updates
  ```

  We only deliver that message if the service is enabled and we did upgrade packages related
  to it. For example, if we had no `esm-infra` package upgrades, the message would be:

  ```
  1 standard LTS security update and 8 esm-apps security updates
  ```

* **expired contract**: If we detect that your contract is expired, we will deliver the following
  message advertising `esm-infra` in the middle of the `apt` command:

  ```
  *Your Ubuntu Pro subscription has EXPIRED*
  The following security updates require Ubuntu Pro with 'esm-infra' enabled:
    libpam0g libpam-modules openssl ntfs-3g git-man libsystemd0 squashfs-tools git openssh-sftp-server udev libpam-runtime isc-dhcp-common libx11-6 libudev1 apport python3-apport systemd-sysv liblz4-1 libpam-systemd systemd libpam-modules-bin openssh-server libx11-data openssh-client libxml2 curl isc-dhcp-client python3-problem-report libcurl3-gnutls libssl1.0.0
  Renew your service at https://ubuntu.com/pro
  ```
 
  Note that if we don't have any package to upgrade related to `esm-infra`, we would deliver instead
  the message:

  ```
  *Your Ubuntu Pro subscription has EXPIRED*
  Renew your service at https://ubuntu.com/pro
  ```

* **contract is about to expire**: Similarly, if we detect that your contract is about to expire,
  we deliver the following message in the middle of the `apt-get` command:

  ```
  CAUTION: Your Ubuntu Pro subscription will expire in 2 days.
  Renew your subscription at https://ubuntu.com/pro to ensure continued security
  coverage for your applications.
  ```

* **contract expired, but in grace period**: Additionally, if we detect that the contract is
  expired, but still in the grace period, the following message will be seen in the middle
  of the `apt-get` command:

  ```
  CAUTION: Your Ubuntu Pro subscription expired on 10 Sep 2021.
  Renew your subscription at https://ubuntu.com/pro to ensure continued security
  coverage for your applications.
  Your grace period will expire in 8 days.
  ```

> **Note**
> For contract expired messages, we only advertise `esm-infra`.


## How are the APT messages generated

We have two distinct `apt` hooks that allow us to deliver those messages when you
are running `apt-get upgrade` or `apt-get dist-upgrade`, they are:

* **apt-esm-hook**: Responsible for delivering the contract expired and ESM services
  advertising. However, the messaging here is created by two distinct steps:

  1. Our [update_messages](what_are_the_timer_jobs.md) timer job create templates for
     the APT messages this hook will deliver. We cannot create the full message on the
     timer job, because we need the accurate package names and count. That information
     can only be obtained when running the `apt-get` command.

     > **Note**
     > This templates will only be produced if some conditions are met. For example,
     > we only produce expired contract templates if the contracts are indeed expired.

  2. When you run either `apt-get upgrade` or `apt-get dist-upgrade`, the hook searches
     for these templates and if they exist, they are populated with the right `apt`
     content and delivered to the user.

* **apt-esm-json-hook**: The json hook is responsible for delivering the package count
  message we mentioned on the `esm package count` item. This hook is used because
  to inject that message on the exact place we want, we need to use a specific apt`
  [json hook](https://salsa.debian.org/apt-team/apt/-/blob/main/doc/json-hooks-protocol.md)
  to communicate with.


> **Note**
> Those hooks are only delivered on LTS releases. This is because the hooks will
> not deliver useful messages on non-LTS due to lack of support for ESM services.

## How are APT configured to deliver those messages

We currently ship the package the `20apt-esm-hook.conf` configuration that
configures both the basic apt hooks to call our `apt-esm-hook` binary, and also
the `json` API of `apt` to call our `apt-esm-json-hook` binary.
