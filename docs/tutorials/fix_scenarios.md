# Using fix command to solve CVE/USNs on the machine

The Ubuntu Pro Client (`pro`) can be used to inspect and resolve
[Common Vulnerabilities and Exposures](https://ubuntu.com/security/cves)(CVE) and [Ubuntu Security Notices](https://ubuntu.com/security/notices) (USN)
on this machine.

Every CVE/USN is fixed by trying to upgrade all of the affected packages described by the CVE or
USN. Sometimes, the packages fixes can only be applied if an Ubuntu Pro service is already enabled on the
machine.

On this tutorial, we will cover the main scenarios that can happen when running the `pro fix` command.

## Prerequisites

In this tutorial, you will use [Multipass](https://multipass.run/) virtual machines (VM).

We have chosen Multipass for this tutorial because it allows us to easily launch VMs while not
requiring any complicated setup for the tool.

To install Multipass on your computer, please run the following command on your machine:

```console
$ sudo snap install multipass
```


## Creating the Xenial Multipass virtual machine

To test some scenarios for the `pro fix` command, we will need to attach a
Pro subscription to the machine. To avoid modifying your machine, let's create
a Xenial Multipass VM instead. Remember to install Multipass as mentioned in the
[Prerequisites](#prerequisites) section. After that, just run the command:

```console
$ multipass launch xenial --name dev-x
```

After running that, let's access the VM by running:

```console
$ multipass shell dev-x
```

Notice that when you run that command, that your terminal username and hostname will change to:

```
ubuntu@dev-x
```

This indicates that you are now inside the VM.

Finally, let's run an `apt update` and `apt upgrade` command on the virtual machine

```console
$ sudo apt update && sudo apt upgrade -y
```

Every time we say: "run the command" our intention will be for
you to run that command on your VM.

## Using `pro fix`

First, let's see what happens on your system when `pro fix` runs. We will choose
to fix a CVE that does not affect the VM,
[CVE-2020-15180](https://ubuntu.com/security/CVE-2020-15180). This CVE address security
issues for the `MariaDB` package, which is not installed on the system. Let's confirm that
it doesn't affect the system by running this command:

```console
$ pro fix CVE-2020-15180
```

You should see an output like this one:

```
CVE-2020-15180: MariaDB vulnerabilities
https://ubuntu.com/security/CVE-2020-15180
No affected source packages are installed.
✔ CVE-2020-15180 does not affect your system.
```

Every `pro fix` output will have a similar output structure where we describe the CVE/USN,
display the affected packages, fix the affected packages and at the end, show if the
CVE/USN is fully fixed in the machine.

You can better see this in a `pro fix` call that does fix a package. Let's install a package
on the VM that we know is associated with [CVE-2020-25686](https://ubuntu.com/security/CVE-2020-25686).
You can install that package by running these commands:

```console
$ sudo apt update
$ sudo apt install dnsmasq=2.75-1
```

Now you can run the following command:

```console
$ sudo pro fix CVE-2020-25686
```

You will then see the following output:

```
CVE-2020-25686: Dnsmasq vulnerabilities
https://ubuntu.com/security/CVE-2020-25686
1 affected package is installed: dnsmasq
(1/1) dnsmasq:
A fix is available in Ubuntu standard updates.
{ apt update && apt install --only-upgrade -y dnsmasq }
✔ CVE-2020-25686 is resolved.
```

```{note}
We need to run the command with sudo because we are now installing a package on the system.
```

Whenever `pro fix` has a package to upgrade, it follows a consistent structure and displays the
following in order

1. The affected package
2. The availability of a fix
3. The location of the fix, if one is available
4. The command that will fix the issue

Also, in the end of the output is the confirmation that the CVE was fixed by the command.
You can confirm that fix was successfully applied by running the same `pro fix` command again:

```
CVE-2020-25686: Dnsmasq vulnerabilities
https://ubuntu.com/security/CVE-2020-25686
1 affected package is installed: dnsmasq
(1/1) dnsmasq:
A fix is available in Ubuntu standard updates.
The update is already installed.
✔ CVE-2020-25686 is resolved.
```

## CVE/USN without released fix

Some CVE/USNs do not have a fix released yet. When that happens, `pro fix` will let you know
about this situation. Before we reproduce that scenario, you will first install a package by running:

```console
$ sudo apt install -y libawl-php
```

Now, you can confirm that scenario by running the following command:

```console
$ pro fix USN-4539-1
```

You will see the following output:

```
USN-4539-1: AWL vulnerability
Found CVEs:
https://ubuntu.com/security/CVE-2020-11728
1 affected source package is installed: awl
(1/1) awl:
Sorry, no fix is available.
1 package is still affected: awl
✘ USN-4539-1 is not resolved.
```

Notice that we inform that the is no fix available and in the last line the commands also
mentions that the USN is not resolved.

## CVE/USN that require an Ubuntu Pro subscription

Some package fixes can only be installed when the machine is attached to an Ubuntu Pro subscription.
When that happens, `pro fix` will let you know about that. To see an example of this scenario,
you can run the following fix command:


```console
$ sudo pro fix USN-5079-2
```

You will see that the command will prompt you like this:

```
USN-5079-2: curl vulnerabilities
Found CVEs:
https://ubuntu.com/security/CVE-2021-22946
https://ubuntu.com/security/CVE-2021-22947
1 affected package is installed: curl
(1/1) curl:
A fix is available in Ubuntu Pro: ESM Infra.
The update is not installed because this system is not attached to a
subscription.

Choose: [S]ubscribe at ubuntu.com [A]ttach existing token [C]ancel
> 
```

You can see that the prompt is asking for an Ubuntu Pro subscription token. Any user with
a Ubuntu One account is entitled to a free personal token to use with Ubuntu Pro.
If you choose the `Subscribe` option on the prompt, the command will ask you to go
to the [Ubuntu Pro portal](https://ubuntu.com/pro/). You can go into that portal
and get yourself a free subscription token by logging in with your
SSO credentials, the same credentials you use for https://login.ubuntu.com.

After getting your Ubuntu Pro token, you can hit `Enter` on the prompt and it will ask you
to provide the token you just obtained. After entering the token you are expected to
see now the following output:

```
USN-5079-2: curl vulnerabilities
Found CVEs:
https://ubuntu.com/security/CVE-2021-22946
https://ubuntu.com/security/CVE-2021-22947
1 affected package is installed: curl
(1/1) curl:
A fix is available in Ubuntu Pro: ESM Infra.
The update is not installed because this system is not attached to a
subscription.

Choose: [S]ubscribe at ubuntu.com [A]ttach existing token [C]ancel
>S
Open a browser to: https://ubuntu.com/pro
Hit [Enter] when subscription is complete.
Enter your token (from https://ubuntu.com/pro) to attach this system:
> TOKEN
{ pro attach TOKEN }
Enabling default service esm-infra
Updating package lists
Ubuntu Pro: ESM Infra enabled
This machine is now attached to 'SUBSCRIPTION'

SERVICE       ENTITLED  STATUS    DESCRIPTION
cis           yes       disabled  Center for Internet Security Audit Tools
esm-infra     yes       enabled   Expanded Security Maintenance for Infrastructure
fips          yes       n/a       NIST-certified core packages
fips-updates  yes       n/a       NIST-certified core packages with priority security updates
livepatch     yes       n/a       Canonical Livepatch service

NOTICES
Operation in progress: pro attach

Enable services with: pro enable <service>

                Account: Ubuntu Pro Client Test
           Subscription: SUBSCRIPTION
            Valid until: 9999-12-31 00:00:00+00:00
Technical support level: essential
{ apt update && apt install --only-upgrade -y curl libcurl3-gnutls }
✔ USN-5079-2 is resolved.
```

We can see that that the attach command was successful, which can be verified by
the status output we see when executing the command. Additionally, we can also observe
that the USN is indeed fixed, which you can confirm by running the command again:

```
N-5079-2: curl vulnerabilities
Found CVEs:
https://ubuntu.com/security/CVE-2021-22946
https://ubuntu.com/security/CVE-2021-22947
1 affected package is installed: curl
(1/1) curl:
A fix is available in Ubuntu Pro: ESM Infra.
The update is already installed.
✔ USN-5079-2 is resolved.
```

```{note}
Even though we are not covering this scenario here, if you have an expired contract,
`pro fix` will detect that and prompt you to attach a new token for your machine.
```

## CVE/USN that requires an Ubuntu Pro service

Now, let's assume that you have attached to an Ubuntu Pro subscription, but when running `pro fix`,
the required service that fixes the issue is not enabled. In that situation, `pro fix` will
also prompt you to enable that service.

To confirm that, run the following command to disable `esm-infra`:

```console
$ sudo pro disable esm-infra
```

Now, you can run the following command:

```console
$ sudo pro fix CVE-2021-44731
```

And you should see the following output (if you type `E` when prompted):

```
CVE-2021-44731: snapd vulnerabilities
https://ubuntu.com/security/CVE-2021-44731
1 affected package is installed: snapd
(1/1) snapd:
A fix is available in Ubuntu Pro: ESM Infra.
The update is not installed because this system does not have
esm-infra enabled.

Choose: [E]nable esm-infra [C]ancel
> E
{ pro enable esm-infra }
One moment, checking your subscription first
Updating package lists
Ubuntu Pro: ESM Infra enabled
{ apt update && apt install --only-upgrade -y ubuntu-core-launcher snapd }
✔ CVE-2021-44731 is resolved.
```

You can observe that the required service was enabled and `pro fix` was able to successfully upgrade
the affected package.

## CVE/USN that requires reboot

When running an `pro fix` command, sometimes we can install a package that requires
a system reboot to complete. The `pro fix` command can detect that and will inform you
about it.

You can confirm this by running the following fix command:

```console
$ sudo pro fix CVE-2022-0778
```

Then you will see the following output:

```
VE-2022-0778: OpenSSL vulnerability
https://ubuntu.com/security/CVE-2022-0778
1 affected package is installed: openssl
(1/1) openssl:
A fix is available in Ubuntu Pro: ESM Infra.
{ apt update && apt install --only-upgrade -y libssl1.0.0 openssl }
A reboot is required to complete fix operation.
✘ CVE-2022-0778 is not resolved.
```

If we reboot the machine and run the command again, you will see that it is indeed fixed:

```
CVE-2022-0778: OpenSSL vulnerability
https://ubuntu.com/security/CVE-2022-0778
1 affected package is installed: openssl
(1/1) openssl:
A fix is available in Ubuntu Pro: ESM Infra.
The update is already installed.
✔ CVE-2022-0778 is resolved.
```

## Partially resolved CVE/USNs

Finally, you might run a `pro fix` command that only partially fixes some of the packages affected.
This happens when only a subset of the packages have available updates to fix for that CVE/USN.
In this case, `pro fix` will inform of which package it can and cannot fix.

But first, let's install some package so we can run `pro fix` to exercise that scenario.

```console
$ sudo apt-get install expat=2.1.0-7 swish-e matanza ghostscript
```

Now, you can run the following command:

```console
$ sudo pro fix CVE-2017-9233
```

And you will see the following command:

```
CVE-2017-9233: Expat vulnerability
https://ubuntu.com/security/CVE-2017-9233
3 affected packages are installed: expat, matanza, swish-e
(1/3, 2/3) matanza, swish-e:
Sorry, no fix is available.
(3/3) expat:
A fix is available in Ubuntu standard updates.
{ apt update && apt install --only-upgrade -y expat }
2 packages are still affected: matanza, swish-e
✘ CVE-2017-9233 is not resolved.
```

We can see that two packages, `matanza` and `swish-e`, don't have any fixes available, but there
is one for `expat`. In that scenario, we install the fix for `expat` and report at the end that
some packages are still affected. Also, observe that in this scenario we mark the CVE/USN as not
resolved.

### Final thoughts

This tutorial has covered the main scenario that can happen to you when running `pro fix`.
If you need more information about the command please feel free to reach the Ubuntu Pro Client team on
`#ubuntu-server` on Libera IRC.

Before you finish this tutorial, exit the VM by running `CTRL-D` and delete it by running
this command on the host machine:

```console
$ multipass delete dev-x
$ multipass purge
```
