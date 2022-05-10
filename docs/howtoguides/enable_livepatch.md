# How to enable Livepatch

Livepatch requires:

* kernel version 4.4 or above (16.04+ delivered via the HWE Kernel https://wiki.ubuntu.com/Kernel/LTSEnablementStack)

To enable, run:

```console
$ sudo ua enable livepatch
```

You should see output like the following, indicating that the Livepatch snap package has
been installed.

```
One moment, checking your subscription first
Installing snapd
Updating package lists
Installing canonical-livepatch snap
Canonical livepatch enabled.
```

To check the status of Livepatch once it has been installed use this command

```console
$ sudo canonical-livepatch status
```

More information: https://ubuntu.com/security/livepatch
