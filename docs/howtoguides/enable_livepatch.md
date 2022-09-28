# How to enable Livepatch

Check if your kernel is supported by Livepatch here: https://ubuntu.com/security/livepatch/docs/kernels

To enable, run:

```console
$ sudo pro enable livepatch
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
