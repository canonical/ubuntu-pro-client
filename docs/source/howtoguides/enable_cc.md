# How to enable CC EAL

> NOTE: CC EAL can be enabled on both Xenial and Bionic, but the installed scripts
which configure CC EAL on those machines will only run on Xenial 16.04.4 and Bionic 18.04.4
point releases.

Common Criteria is supported only on 16.04 and 18.04. For more information on it,
please see https://ubuntu.com/security/cc

To enable it through UA, please run:

```console
$ sudo ua enable cc-eal
```

You should see output like the following, indicating that the CC EAL packages has
been installed.

```
(This will download more than 500MB of packages, so may take some time.)
Installing CC EAL2 packages
CC EAL2 enabled
Please follow instructions in /usr/share/doc/ubuntu-commoncriteria/README to configure EAL2
```
