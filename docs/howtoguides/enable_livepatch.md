# How to manage Livepatch

For Ubuntu LTS releases, [Livepatch](https://ubuntu.com/security/livepatch) is
automatically enabled after you attach the Ubuntu Pro subscription. However,
you can choose to disable it initially via the dashboard, and then enable it
at a later time from the command line using the Ubuntu Pro Client (`pro`). 

## Check the status of the Livepatch service

After you have attached your subscription and installed the
`ubuntu-advantage-tools` package, you can check if Livepatch is enabled by
running the following command:

```console
pro status
```

```console
SERVICE          ENTITLED  STATUS    DESCRIPTION
esm-apps         yes       enabled   Expanded Security Maintenance for Applications
esm-infra        yes       enabled   Expanded Security Maintenance for Infrastructure
livepatch        yes       enabled   Canonical Livepatch service
realtime-kernel  yes       disabled  Ubuntu kernel with PREEMPT_RT patches integrated
```

## How to enable Livepatch

If Livepatch is disabled and you want to enable it, run the following command:

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

## Check Livepatch status after installation
To check the status of the Livepatch client once it has been installed use the
following command:

```console
$ sudo canonical-livepatch status
```

### Unsupported kernels

Although you can enable Livepatch on an unsupported kernel, since patches are
kernel-specific, you will not receive any updates from Livepatch if your kernel
is not supported. The `canonical-livepatch status` command will warn you if
your kernel is unsupported (output truncated for brevity):

```console
...
server check-in: succeeded
kernel state: ✗ kernel not supported by Canonical 
patch state: ✓ no livepatches needed for this kernel yet
...
```

You can also check [the support matrix](https://ubuntu.com/security/livepatch/docs/kernels)
to see if your kernel is supported by Livepatch. To find out more, refer to
this explanation of
[how Livepatch works](https://ubuntu.com/security/livepatch/docs/livepatch/explanation/howitworks).

## How to disable Livepatch

Enabling Livepatch installs the Livepatch client as snap package, and there are
a few possible ways to disable it. To stop the service, follow this short guide
on [how to disable the client](https://ubuntu.com/security/livepatch/docs/livepatch/how-to/disable)
from the Livepatch documentation.

## Notes

- For more information about the Livepatch client, refer to the 
  [official Livepatch client documentation](https://ubuntu.com/security/livepatch/docs).

- Livepatch is not compatible with FIPS-certified kernels or with the
  Real-Time Kernel, and should not be enabled if you wish to use those services.
  If Livepatch is enabled and you try to enable those other services, you will
  need to disable Livepatch first.
