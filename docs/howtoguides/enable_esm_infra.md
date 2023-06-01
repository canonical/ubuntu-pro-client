# How to manage Expanded Security Maintenance (ESM) services

For Ubuntu LTS releases, ESM for Infrastructure (`esm-infra`) and ESM for
Applications (`esm-apps`) are automatically enabled after you attach the
Ubuntu Pro Client subscription to your account. However, if you chose to
disable them initially, you can enable them at any time from the command line
using the Ubuntu Pro Client (`pro`).

## Make sure `pro` is up-to-date

All systems come with `pro` pre-installed through the `ubuntu-advantage-tools`
package. To make sure that you're running the latest version of `pro`, run the
following commands:

```console
sudo apt update && sudo apt install ubuntu-advantage-tools
```

## Check the status of the services

After you have attached your subscription and updated the
`ubuntu-advantage-tools` package, you can check if `esm-apps` and `esm-infra`
are enabled by running the following command:

```bash
pro status
```

This will show you which services are enabled or disabled on your machine:

```console
SERVICE          ENTITLED  STATUS    DESCRIPTION
esm-apps         yes       enabled   Expanded Security Maintenance for Applications
esm-infra        yes       enabled   Expanded Security Maintenance for Infrastructure
livepatch        yes       enabled   Canonical Livepatch service
realtime-kernel  yes       disabled  Ubuntu kernel with PREEMPT_RT patches integrated
```

## Enable `esm-apps` and `esm-infra`

If either of the `esm-apps` or `esm-infra` services are disabled and you want
to enable them, run the following command to enable ESM-Infra:

```bash
sudo pro enable esm-infra
```

Or the following for ESM-Apps:

```bash
sudo pro enable esm-apps
```

## Update your packages

When you enable the ESM-Infra and/or ESM-Apps repositories, especially on
Ubuntu 14.04 and 16.04, you may see a number of package updates available that
were not available previously.

Even if your system indicated that it was up to date before enabling
`esm-infra` or `esm-apps`, make sure to check for new package updates after
you enable them:

```bash
sudo apt upgrade
```

If you have cron jobs set to install updates, or other unattended upgrades
configured, be aware that this will likely result in a number of packages being
updated with the `esm-infra` and `esm-apps` content.

Running `apt upgrade` will apply all available package updates, including
the ones in `esm-infra` and `esm-apps`.

## Disable the services

If you wish to disable the services, you can use the following command to
disable ESM-Infra:

```bash
sudo pro disable esm-infra
```

Or the following command to disable ESM-Apps:

```bash
sudo pro disable esm-apps
```

## Notes

- For more information about ESM-Apps and ESM-Infra, see
[our explanatory guide](../explanations/about_esm).

