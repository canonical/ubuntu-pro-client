# UA related messages on MOTD

When UA is installed on the system, it delivers custom messages on [MOTD](https://wiki.debian.org/motd).
Those messages are generated directly by two different sources:

* **python script**: The [update-notifier](https://wiki.ubuntu.com/UpdateNotifier) deliver a script
  called `apt_check.py`. Considering UA related information, this script is responsible for:
  
  * inform the user about the status of one of the ESM services, `esm-apps` if the machine is a
    LTS series or `esm-infra` if the series is on ESM mode.
  * showing the number of `esm-infra` or `esm-apps` packages that can be upgraded in the machine

  For example, this is the output of the `apt_check.py` script on a LTS machine when both of
  those services are enabled:

  ```
  UA Apps: Extended Security Maintenance (ESM) is enabled.

  11 updates can be applied immediately.
  5 of these updates are UA Apps: ESM security updates.
  1 of these updates is a UA Infra: ESM security update.
  5 of these updates are standard security updates.
  To see these additional updates run: apt list --upgradable
  ```

  Note that if we were running this on a ESM series, we would instead see `esm-infra` being
  advertised:

  ```
  UA Infra: Extended Security Maintenance (ESM) is enabled.

  11 updates can be applied immediately.
  5 of these updates are UA Apps: ESM security updates.
  1 of these updates is a UA Infra: ESM security update.
  5 of these updates are standard security updates.
  To see these additional updates run: apt list --upgradable
  ```

  Now considering the scenario were one of those services is not enabled. For example, if
  `esm-apps` was not enabled, the output will be:

  ```
  UA Apps: Extended Security Maintenance (ESM) is not enabled.
  
  6 updates can be applied immediately.
  1 of these updates is a UA Infra: ESM security update.
  5 of these updates are standard security updates.
  To see these additional updates run: apt list --upgradable
  
  5 additional security updates can be applied with UA Apps: ESM
  Learn more about enabling UA Infra: ESM service for Ubuntu 16.04 at
  https://ubuntu.com/16-04
  ```

  In the end of the output we can see the number of packages that could
  be upgraded if that service was enabled. Note that we would deliver the same information
  for `esm-infra` if the service was disabled and the series running on the machine is on ESM
  state.

* **UA timer jobs**: One of the timer jobs UA has is used to insert additional messages into MOTD.
  Those messages will be always delivered before or after the content created by the python
  script delivered by `update-notifier`. Those additional messages are generated when UA detect
  some conditions on the machine. They are:

  * **subscription expired**: When the UA subscription is expired, UA will deliver the following
    message after the `update-notifier` message:

    ```
    *Your Ubuntu Pro: ESM Infra subscription has EXPIRED*

    2 additional security updates could have been applied via Ubuntu Pro: ESM Infra.
    Renew your UA services at https://ubuntu.com/advantage

    Ubuntu comes with ABSOLUTELY NO WARRANTY, to the extent permitted by applicable law.
    ```

  * **subscription about to expire**: When the UA subscription is about to expire, we deliver the
    following message after the `update-notifier` message:

    ```
    CAUTION: Your Ubuntu Pro: ESM Infra service will expire in 5 days.
    Renew UA subscription at https://ubuntu.com/advantage to ensure
    continued security coverage for your applications.
    ```

  * **subscription expired but within grace period**: When the UA subscription is expired, but is
    still within the grace period, we deliver the following message after the `update-notifier`
    script:

    ```
    CAUTION: Your Ubuntu Pro: ESM Infra service expired on 10 Sep 2021.
    Renew UA subscription at https://ubuntu.com/advantage to ensure
    continued security coverage for your applications.
    Your grace period will expire in 9 days.
    ```

  * **advertising esm-apps service**: When we detect that `esm-apps` is supported and not enabled
    in the system, we advertise it using the following message that is delivered before the
    `update-notifier` message:

    ```
    * Introducing Extended Security Maintenance for Applications.
      Receive updates to over 30,000 software packages with your
      Ubuntu Advantage subscription. Free for personal use

        https://ubuntu.com/16-04 
    ```

  Note that we could also advertise the `esm-infra` service instead. This will happen
  if you use an ESM release. Additionally, the same can for the url we use to advertise the
  esm service, we adapt it based on the series that is running on the machine.

  Additionally, all of those UA custom messages are delivered into
  `/var/lib/ubuntu-advantage/messages`. We also add custom scripts into `/etc/update-motd.d` to
  check if those messages exist and if they do, insert them on the full MOTD message.
