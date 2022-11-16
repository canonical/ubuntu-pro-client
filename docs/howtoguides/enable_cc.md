# How to enable CC EAL

> NOTE: CC EAL can be enabled on both Xenial and Bionic, but the installed scripts
which configure CC EAL on those machines will only run on Xenial 16.04.4 and Bionic 18.04.4
point releases.

Common Criteria is supported only on 16.04 and 18.04. For more information on it,
please see https://ubuntu.com/security/cc

## Enable and auto-install

To enable it through UA, please run:

```console
$ sudo pro enable cc-eal
```

You should see output like the following, indicating that the CC EAL packages has
been installed.

```
(This will download more than 500MB of packages, so may take some time.)
Installing CC EAL2 packages
CC EAL2 enabled
Please follow instructions in /usr/share/doc/ubuntu-commoncriteria/README to configure EAL2
```

## Enable and manually install

```{important}
The --access-only flag is introduced in version 27.11
```

If you would like to enable access to the CC EAL apt repository but not install the packages right away, use the `--access-only` flag while enabling.

```console
$ sudo pro enable cc-eal --access-only
```

With that extra flag you'll see output like the following:

```
One moment, checking your subscription first
Updating package lists
Skipping installing packages: ubuntu-commoncriteria
CC EAL2 access enabled
```

To install the packages you can then run:

```console
$ sudo apt install ubuntu-commoncriteria
```
