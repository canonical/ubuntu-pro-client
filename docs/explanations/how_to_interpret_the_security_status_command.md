# What does `security-status` do?

The `security-status` command provides an overview of all the packages
installed on your machine, and the security coverage that applies to those
packages.

The output of the `security-status` command varies, depending on the configuration of the machine you run it on. In this article, we'll take a look at the different outputs of `security-status` and the situations in which you might see them.

## Command output

If you run the `pro security-status` command, the first blocks of information
you see look like:

```
2871 packages installed:
     2337 packages from Ubuntu Main/Restricted repository
     504 packages from Ubuntu Universe/Multiverse repository
     8 packages from third parties
     22 packages no longer available for download

To get more information about the packages, run
    pro security-status --help
for a list of available options.
```

Those are counts for the `apt` packages installed in the system, sorted
between the packages in main, universe, third party packages, and packages
that are no longer available. You will also see a hint to run
`pro security-status --help` to get more information.

### `apt update` hint

To get accurate package information, the `apt` caches must be up to date. If
your cache was not updated recently, you may see a message in the output with
a hint to update.

```
The system apt cache may be outdated. Make sure to run
    sudo apt-get update
to get the latest package information from apt.
```

### LTS coverage

If `esm-infra` is disabled in your system, main/restricted packages will be
covered during the LTS period - this information is presented right after the
hints. A covered system will present this message:

```
This machine is receiving security patching for Ubuntu Main/Restricted
repository until <year>.
```

On a system where the LTS period ended, you'll see:

```
This machine is NOT receiving security patches because the LTS period has ended
and esm-infra is not enabled.
```

### Ubuntu Pro coverage

An Ubuntu Pro subscription provides more security coverage than a standard LTS.
The next blocks of information are related to Ubuntu Pro itself:

```
This machine is attached to an Ubuntu Pro subscription.

Main/Restricted packages are receiving security updates from
Ubuntu Pro with 'esm-infra' enabled until 2032.

Universe/Multiverse packages are receiving security updates from
Ubuntu Pro with 'esm-apps' enabled until 2032. You have received 21 security
updates.
```

This system is already attached to Pro! It is a Jammy machine, which has
installed some updates from `esm-apps`. Running the same command on a Xenial
system without Pro enabled, the output looks like:

```
This machine is NOT attached to an Ubuntu Pro subscription.

Ubuntu Pro with 'esm-infra' enabled provides security updates for
Main/Restricted packages until 2026. There are 170 pending security updates.

Ubuntu Pro with 'esm-apps' enabled provides security updates for
Universe/Multiverse packages until 2026. There is 1 pending security update.

Try Ubuntu Pro with a free personal subscription on up to 5 machines.
Learn more at https://ubuntu.com/pro
```

There are lots of `esm-infra` updates for this machine, and even an `esm-apps`
update. The hint in the end of the output has a link to the main Pro website,
so the user can learn more about Pro and get their subscription.

### Interim releases

If you are running an interim release, the output is slightly different because
there are no Ubuntu Pro services available. You will still see the package
counts and support period though - your main/restricted packages are supported
for 9 months from the release date.

```
613 packages installed:
    601 packages from Ubuntu Main/Restricted repository
    12 packages from Ubuntu Universe/Multiverse repository

To get more information about the packages, run
    pro security-status --help
for a list of available options.

Main/Restricted packages receive updates until 1/2024.

Ubuntu Pro is not available for non-LTS releases.
```

### Optional flags for specific package sets

Some flags can be passed to `security-status` to get information about coverage
of specific package sets. As an example, let's look at the output of
`pro security-status --esm-infra`:

```
442 packages installed:
    441 packages from Ubuntu Main/Restricted repository

Main/Restricted packages are receiving security updates from
Ubuntu Pro with 'esm-infra' enabled until 2026. You have received 3 security
updates. There are 160 pending security updates.

Run 'pro help esm-infra' to learn more

Installed packages with an available esm-infra update:
( ... list of packages ... )

Installed packages with an esm-infra update applied:
( ... list of packages ... )

Further installed packages covered by esm-infra:
( ... list of packages ... )

For example, run:
    apt-cache show tcpdump
to learn more about that package.
```

Besides the support information of main/restricted (which Ubuntu Pro with
`esm-infra` extends) there are lists of:
- packages which have some updated version available in esm-infra repositories
- packages which have an installed version from the esm-infra repositories
- packages which are covered by esm-infra

You will see a similar output when running `pro security-status --esm-apps`,
but with information regarding universe/multiverse packages.

You can also get a list of the third-party packages installed in the system:

```
$ pro security-status --thirdparty
2871 packages installed:
     8 packages from third parties

Packages from third parties are not provided by the official Ubuntu
archive, for example packages from Personal Package Archives in Launchpad.

Packages:
( ... list of packages ... )

For example, run:
    apt-cache show <package_name>
to learn more about that package.
```

And also a list of unavailable packages (which no longer have any installation
source):

```
$ pro security-status --unavailable
2871 packages installed:
     22 packages no longer available for download

Packages that are not available for download may be left over from a
previous release of Ubuntu, may have been installed directly from a
.deb file, or are from a source which has been disabled.

Packages:
( ... list of packages ... )


For example, run:
    apt-cache show <package_name>
to learn more about that package.
```

## Machine-readable output

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

Let's understand what each key means in the output of the
`pro security-status --format yaml` command:

### `summary`

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

### `packages`

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

### `livepatch`

This displays Livepatch-related information. Currently, the only information
presented is **`fixed_cves`**. This represents a list of CVEs that were fixed
by Livepatches applied to the kernel.
