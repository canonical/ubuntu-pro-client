# Ubuntu Pro related messages on MOTD

When Ubuntu Pro Client (`pro`) is installed on the system, it delivers custom messages on [MOTD](https://wiki.debian.org/motd).
Those messages are generated directly by two different sources:

* **python script**: The [update-notifier](https://wiki.ubuntu.com/UpdateNotifier) deliver a script
  called `apt_check.py`. Considering Ubuntu Pro related information, this script is responsible for:
  
  * inform the user about the status of one of the ESM services, `esm-apps` if the machine is a
    LTS series or `esm-infra` if the series is on ESM mode.
  * showing the number of `esm-infra` or `esm-apps` packages that can be upgraded in the machine

  For example, this is the output of the `apt_check.py` script on a LTS machine when both of
  those services are enabled:

  ```
  Expanded Security Maintenance for Applications is enabled.

  11 updates can be applied immediately.
  5 of these updates are ESM Apps security updates.
  1 of these updates is a ESM Infra security update.
  5 of these updates are standard security updates.
  To see these additional updates run: apt list --upgradable
  ```

  Note that if we were running this on a ESM series, we would instead see `esm-infra` being
  advertised:

  ```
  Expanded Security Maintenance Infrastructure is enabled.

  11 updates can be applied immediately.
  5 of these updates are ESM Apps security updates.
  1 of these updates is a ESM Infra security update.
  5 of these updates are standard security updates.
  To see these additional updates run: apt list --upgradable
  ```

  Now considering the scenario were one of those services is not enabled. For example, if
  `esm-apps` was not enabled, the output will be:

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

  In the end of the output we can see the number of packages that could
  be upgraded if that service was enabled. Note that we would deliver the same information
  for `esm-infra` if the service was disabled and the series running on the machine is on ESM
  state.

* **Ubuntu Pro timer jobs**: One of the timer jobs Ubuntu Pro has is used to insert additional messages into MOTD.
  Those messages will be always delivered before or after the content created by the python
  script delivered by `update-notifier`. Those additional messages are generated when `pro` detects
  some conditions on the machine. They are:

  * **subscription expired**: When the Ubuntu Pro subscription is expired, `pro` will deliver the following
    message after the `update-notifier` message:

    ```
    *Your Ubuntu Pro subscription has EXPIRED*
    2 additional security update(s) require Ubuntu Pro with 'esm-infra' enabled.
    Renew your service at https://ubuntu.com/pro
    ```

  * **subscription about to expire**: When the Ubuntu Pro subscription is about to expire, we deliver the
    following message after the `update-notifier` message:

    ```
    CAUTION: Your Ubuntu Pro subscription will expire in 2 days.
    Renew your subscription at https://ubuntu.com/pro to ensure continued security
    coverage for your applications.
    ```

  * **subscription expired but within grace period**: When the Ubuntu Pro subscription is expired, but is
    still within the grace period, we deliver the following message after the `update-notifier`
    script:

    ```
    CAUTION: Your Ubuntu Pro subscription expired on 10 Sep 2021.
    Renew your subscription at https://ubuntu.com/pro to ensure continued security
    coverage for your applications.
    Your grace period will expire in 9 days.
    ```

  * **advertising esm-apps service**: When we detect that `esm-apps` is supported and not enabled
    in the system, we advertise it using the following message that is delivered before the
    `update-notifier` message:

    ```
    * Introducing Expanded Security Maintenance for Applications.
      Receive updates to over 25,000 software packages with your
      Ubuntu Pro subscription. Free for personal use

        https://ubuntu.com/16-04 
    ```

  Note that we could also advertise the `esm-infra` service instead. This will happen
  if you use an ESM release. Additionally, the the url we use to advertise the service is different
  based on the series that is running on the machine.

  Additionally, all of those Ubuntu Pro custom messages are delivered into
  `/var/lib/ubuntu-advantage/messages`. We also add custom scripts into `/etc/update-motd.d` to
  check if those messages exist and if they do, insert them on the full MOTD message.
