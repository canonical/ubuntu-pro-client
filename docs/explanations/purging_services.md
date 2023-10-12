# Disabling and purging services

All services enabled using the Pro Client can be disabled using the command line:

```bash
$ sudo pro disable <service-name>
```

When you disable a service, the Client will remove all access to that specific service's packages and sources in the system. However, only the access is removed - the packages (debs, snaps) installed when the service was enabled will remain in your system.

For example, the command
```bash
$ sudo pro disable esm-apps
```
will remove the `sources.list` entry for esm-apps, and also the authentication information that granted access to the packages, but not the debs installed from the esm-apps repository.

On the same line, the command
```bash
$ sudo pro disable livepatch
```
will disable the Livepatch service, but the `canonical-livepatch` snap will still be installed on the system (although inactive).

If there are other services which depend on the service being disabled, those need to be disabled too. A prompt in the CLI will list those and and ask to disable them. The `--assume-yes` flag can be used to automatically accept this prompt.

## What does `purge` mean in this context?

Disabling and **purging** a service will have a similar effect to what is done by [`ppa-purge`](https://launchpad.net/ppa-purge): it will remove access to the sources from where the service packages can be obtained, and then make a best-effort attempt to downgrade those packages back to their Ubuntu versions (the ones published in the Ubuntu Archive).

If a package is specific to the given service (`ubuntu-fips` for the FIPS related services, for example) then it will be removed during the purge process, when possible.

```{warning}
The operation of reverting/uninstalling packages may leave the system in an undesired state, due to packages not meeting dependencies (partial or broken system caches) or due to the removal of kernels when alternative kernels are not working properly. Therefore, the `purge` feature is aimed at users/administrators who understand the impacts.
```

## Using the CLI to disable and purge a service

First of all it is important to note that this is an ***experimental feature***, so although it is available it should be used with care and discretion.

To purge a service, use the CLI command:
```bash
$ sudo pro disable <service-name> --purge
```

We recommend only using purge when you are able to monitor the screen. Since the purge feature has the potential to do serious accidental damage to a system if used unattended (for example, in a script), the --assume-yes flag was made incompatible with the --purge flag.

Because packages are being uninstalled/reinstalled, the execution of the `disable` command with `--purge` may take a while to complete.

## What happens when I purge:

### - livepatch, realtime-kernel, landscape

These services do not currently support the `--purge` operation.

### - anbox, cc-eal, cis/usg, esm-apps, esm-infra*, ros (and ros-updates)

When these services are disabled with `--purge`, the sources and authentication will be removed first. Then, packages that are available only in the service-specific APT repository will be removed from the system.

The origin is detected based on the `origin` metadata defined in `apt` for all packages in this repository.

Then, for the packages that are also present in the Ubuntu archives, there will be a downgrade to the highest possible version in the archive. Downgrade operations are the most common because the packages for specific services usually have higher version strings than the counterparts in the archive.

Note that purging a service often results in the installation of newer versions of packages than were originally present in the system (i.e., before the given service was enabled). It is important to use the latest versions available in the archive to guarantee that dependency chains are resolved - in other words, that there are no broken dependencies between packages.

```{note}
\* Disabling `esm-infra` with `--purge` may involve removing a kernel, see below for more information.
```

### - FIPS (and fips-updates/fips-preview)

In the case of FIPS-related services (and in some cases, `esm-infra`), there is an extra consideration when purging the packages: there may be Linux kernel packages among the ones to be removed/downgraded.

In this case, the Pro Client will look for at least one more kernel installed in the system. This check is performed looking at the `apt` packages installed, and matching the version strings to `vmlinu[z|x]` files in `/boot`.

If no other kernel is found in the system, then the current kernel cannot be removed. The Client will warn the user and abort the operation.

Kernels which are manually compiled and installed, or that are not shipped in Ubuntu as APT packages will *not* be considered and validated.

If another Ubuntu kernel is found in the system, `--purge` will proceed to remove and downgrade packages normally. In the process, the user will be warned that a kernel is being removed, and that it is their responsibility to make sure the alternative kernels can be booted and are working.

A reboot is always needed when kernel packages are changed when purging a service.
