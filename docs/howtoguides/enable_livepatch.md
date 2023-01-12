# How to enable Livepatch

```{important}
Check if your kernel is supported by Livepatch here: 
https://ubuntu.com/security/livepatch/docs/kernels
```

To enable Livepatch, run:

```console
$ sudo pro enable livepatch
```

You should see output like the following, indicating that the Livepatch snap
package has been installed successfully:

```
One moment, checking your subscription first
Installing snapd
Updating package lists
Installing canonical-livepatch snap
Canonical livepatch enabled.
```

To check the status of Livepatch once it has been installed use the following
command:

```console
$ sudo canonical-livepatch status
```

```{seealso}
For more information, see: https://ubuntu.com/security/livepatch
```
