# What does `security-status` do?

The `security-status` command is used to get an overview of the packages
installed on your machine.

If you run the `pro security-status --format yaml` command on your machine, you
should expect to see an output that follows this structure:

```
_schema_version: '0.1'
summary:
  num_esm_apps_packages: 0
  num_esm_apps_updates: 0
  num_esm_infra_packages: 1
  num_esm_infra_updates: 1
  num_main_packages: 70
  num_multiverse_packages: 10
  num_restricted_packages: 10
  num_third_party_packages: 0
  num_universe_packages: 9
  num_installed_packages: 100
  num_standard_security_updates: 0
  ua:
    attached: true
    enabled_services:
    - esm-apps
    - esm-infra
    entitled_services:
    - esm-apps
    - esm-infra
packages:
- origin: esm.ubuntu.com
  package: zlib1g
  service_name: esm-infra
  status: upgrade_available
  version: 1:1.2.8.dfsg-2ubuntu4.3+esm1
  download_size: 123456
livepatch:
  fixed_cves:
    - Name: cve-2013-1798
      Patched: true
```

Let's understand what each key means in the output of the `pro security-status`
command:

## `summary`

This provides a summary of the system related to Ubuntu Pro and the different
package sources in the system:

* **`num_installed_packages`**: The total number of installed packages on the
  system.
* **`num_esm_apps_packages`**: The number of packages installed from `esm-apps`.
* **`num_esm_apps_updates`**: The number of `esm-apps` package updates available
  to the system.
* **`num_esm_infra_packages`**: The number of packages installed from
  `esm-infra`.
* **`num_esm_infra_updates`**: The number of `esm-infra` package updates
  available to the system.
* **`num_main_packages`**: The number of packages installed from the `main`
  archive component.
* **`num_multiverse_packages`**: The number of packages installed from the
  `multiverse` archive component.
* **`num_restricted_packages`**: The number of packages installed from the
  `restricted` archive component.
* **`num_third_party_packages`** : The number of packages installed from
  `third party` sources.
* **`num_universe_packages`**: The number of packages installed from the
  `universe` archive component.
* **`num_unknown_packages`**: The number of packages installed from sources not
  known to `apt` (e.g., those installed locally through `dpkg` or packages
  without a remote reference).
* **`num_standard_security_updates`**: The number of standard security updates
  available to the system.

```{note}
  It is worth mentioning here that the `_updates` fields are presenting the
  number of **security** updates for **installed** packages. For example, let's
  assume your machine has a universe package that has a security update from
  `esm-infra`. The count will be displayed as:

  ```
  num_esm_infra_packages: 0
  num_esm_infra_updates: 1
  num_universe_packages: 1
  ```

  After upgrading the system, the count will turn to:

  ```
  num_esm_infra_packages: 1
  num_esm_infra_updates: 0
  num_universe_packages: 0
  ```
```

* **`ua`**: An object representing the state of Ubuntu Pro on the system:
  * **`attached`**: If the system is attached to an Ubuntu Pro subscription.
  * **`enabled_services`**: A list of services that are enabled on the system.
    If unattached, this will always be an empty list.
  * **`entitled_services`**: A list of services that are entitled on your
    Ubuntu Pro subscription. If unattached, this will always be an empty list.

## `packages`

This provides a list of security updates for packages installed on the system.
Every entry on the list will follow this structure:

* **`origin`**: The host where the update comes from.
* **`package`**: The name of the package.
* **`service_name`**: The service that provides the package update. It can be
  one of: `esm-infra`, `esm-apps` or `standard-security`.
* **`status`**: The status for this update. It will be one of:
  * **"upgrade_available"**: The package can be upgraded right now.
  * **"pending_attach"**: The package needs an Ubuntu Pro subscription attached
    to be upgraded.
  * **"pending_enable"**: The machine is attached to an Ubuntu Pro subscription,
    but the service required to provide the upgrade is not enabled.
  * **"upgrade_unavailable"**: The machine is attached, but the contract is not
    entitled to the service which provides the upgrade.
* **`version`**: The update version.
* **`download_size`**: The number of bytes that would be downloaded in order to
  install the update.

## `livepatch`

This displays Livepatch-related information. Currently, the only information
presented is **`fixed_cves`**. This represents a list of CVEs that were fixed
by Livepatches applied to the kernel.
