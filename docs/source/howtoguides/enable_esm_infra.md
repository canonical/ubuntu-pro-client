# How to enable ESM Infra

For Ubuntu LTS releases, ESM Infra will be automatically enabled after attaching
the UA client to your account. After ubuntu-advantage-tools is installed and your machine is
attached, ESM Infra should be enabled. If ESM Infra is not enabled, you can enable it
with the following command:

```console
$ sudo ua enable esm-infra
```

With the ESM Infra repository enabled, specially on Ubuntu 14.04 and 16.04, you may see
a number of additional package updates available that were not available previously.
Even if your system had indicated that it was up to date before installing the
ubuntu-advantage-tools and attaching, make sure to check for new package updates after
ESM Infra is enabled using apt upgrade. If you have cron jobs set to install updates, or other
unattended upgrades configured, be aware that this will likely result in a number of package updates
with the ESM content.

Running apt upgrade will now apply all of package updates available, including the ones in ESM.

```console
$ sudo apt upgrade
```

More information: https://ubuntu.com/security/esm
