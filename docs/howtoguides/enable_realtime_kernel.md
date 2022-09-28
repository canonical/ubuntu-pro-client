# How to enable Real-Time Kernel

> **Warning**:
> Real-Time Kernel is currently in beta.

Real-Time Kernel is supported only on 22.04. For more information on it,
please see https://ubuntu.com/realtime-kernel

## Enable and auto-install

To enable it through UA, please run:

```console
$ sudo pro enable realtime-kernel --beta
```

You'll need to acknowledge a warning and then you should see output like the following, indicating that the Real-Time Kernel package has been installed.

```
One moment, checking your subscription first
The real-time kernel is a beta version of the 22.04 Ubuntu kernel with the
PREEMPT_RT patchset integrated for x86_64 and ARM64.

This will change your kernel. You will need to manually configure grub to
revert back to your original kernel after enabling real-time.

Do you want to continue? [ default = Yes ]: (Y/n) yes
Updating package lists
Installing Real-Time Kernel packages
Real-Time Kernel enabled
A reboot is required to complete install.
```

After rebooting you'll be running the Real-Time Kernel!

## Enable and manually install

> **Note**
> The --access-only flag is introduced in version 27.11

If you would like to enable access to the Real-Time Kernel apt repository but not install the kernel right away, use the `--access-only` flag while enabling.

```console
$ sudo pro enable realtime-kernel --beta --access-only
```

With that extra flag you'll see output like the following:

```
One moment, checking your subscription first
Updating package lists
Skipping installing packages: ubuntu-realtime
Real-Time Kernel access enabled
```

To install the kernel you can then run:

```console
$ sudo apt install ubuntu-realtime
```

You'll need to reboot after installing to boot into the Real-Time Kernel.
