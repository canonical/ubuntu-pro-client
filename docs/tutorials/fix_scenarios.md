# Use `pro fix` to solve CVE/USN

The Ubuntu Pro Client (`pro`) can be used to inspect and resolve
[Common Vulnerabilities and Exposures](https://ubuntu.com/security/cves) (CVE)
and [Ubuntu Security Notices](https://ubuntu.com/security/notices) (USN)
on your machine.

Every CVE/USN is fixed by trying to upgrade all of the affected packages
described by the CVE or USN. Sometimes, the package fixes can only be applied
if an Ubuntu Pro service is already enabled on your machine.

In this tutorial, we will introduce the `pro fix` command and test some common
scenarios that you may encounter.

## How to use this tutorial

The commands in each code block can be copied and pasted directly into your
terminal. You can use the "copy code" button to the right-hand side of the block
and this will copy the code for you (without the command prompt!).

## Install Multipass

In this tutorial, we will use a Xenial Multipass virtual machine (VM) to avoid
making any modifications to your machine. We have chosen
[Multipass](https://multipass.run/) for this tutorial because it allows us to
easily launch VMs without requiring any complicated setup.

To install Multipass on your computer, please run the following command on your
machine:

```console
$ sudo snap install multipass
```

## Create the Xenial Multipass virtual machine

Now that we have installed Multipass, we can launch our Multipass VM by running:

```console
$ multipass launch xenial --name dev-x
```

Now we can access the VM easily by running the command:

```console
$ multipass shell dev-x
```

Notice that your terminal username and hostname will change to:

```
ubuntu@dev-x
```

This indicates that you are now inside the VM.

Finally, let's run `apt update` and `apt upgrade` on the VM to make sure we are
operating on the correct version:

```console
$ sudo apt update && sudo apt upgrade -y
```

From now on, every time we say: "run the command" our intention is for you to
run that command in your VM.

## Use `pro fix`

First, let's see what happens to your system when `pro fix` runs. We will choose
to fix a CVE that does not affect the VM -- in this case,
[CVE-2020-15180](https://ubuntu.com/security/CVE-2020-15180). This CVE address
security issues for the `MariaDB` package, which is not installed on the system.
Let's first confirm that it doesn't affect the system by running this command:

```console
$ pro fix CVE-2020-15180
```

You should see an output like this:

```
CVE-2020-15180: MariaDB vulnerabilities
https://ubuntu.com/security/CVE-2020-15180

No affected source packages are installed.

✔ CVE-2020-15180 does not affect your system.
```

Every `pro fix` output has a similar output structure: it describes the
CVE/USN; displays the affected packages; fixes the affected packages; and at the
end, shows if the CVE/USN is fully fixed in the machine.

This is better demonstrated in a `pro fix` call that *does* fix a package!
Let's install a package on the VM that we know is associated with
[CVE-2020-25686](https://ubuntu.com/security/CVE-2020-25686).
You can install the package by running these commands:

```console
$ sudo apt update
$ sudo apt install dnsmasq=2.75-1
```

Now, let's run `pro fix` on the package:

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
We need to run the command with `sudo` because we are now installing a package
on the system.
```

Whenever `pro fix` has a package to upgrade, it follows a consistent structure
and displays the following, in this order:

1. The affected package
2. The availability of a fix
3. The location of the fix, if one is available
4. The command that will fix the issue

Also, at the end of the output you can see confirmation that the CVE was fixed
by the command. Just to confirm that the fix was successfully applied, let's
run the `pro fix` command again, and we should now see the following:

```
CVE-2020-25686: Dnsmasq vulnerabilities
https://ubuntu.com/security/CVE-2020-25686

1 affected package is installed: dnsmasq
(1/1) dnsmasq:
A fix is available in Ubuntu standard updates.
The update is already installed.

✔ CVE-2020-25686 is resolved.
```

## CVE/USN without a released fix

Some CVE/USN do not have a fix released yet. When that happens, `pro fix` will
let you know! Before we reproduce this scenario, let us first install a package
that we know has no fix available by running:

```console
$ sudo apt-get install -y expat=2.1.0-7 swish-e matanza ghostscript
```

Now, we can confirm that there is no fix by running the following command:

```console
$ pro fix CVE-2017-9233
```

You will see the following output:

```
CVE-2017-9233: Coin3D vulnerability
  - https://ubuntu.com/security/CVE-2017-9233

3 affected source packages are installed: expat, matanza, swish-e
(1/3, 2/3) matanza, swish-e:
Ubuntu security engineers are investigating this issue.
(3/3) expat:
A fix is available in Ubuntu standard updates.
{ apt update && apt install --only-upgrade -y expat }

2 packages are still affected: matanza, swish-e
✘ CVE-2017-9233 is not resolved.
```

As you can see, we are informed by `pro fix` that some packages do not have a fix available. In
the last line, we can also see that the CVE is not resolved.

## CVE/USN that require an Ubuntu Pro subscription

Some package fixes can only be installed when the machine is attached to an
Ubuntu Pro subscription. When that happens, `pro fix` will let you know about
that. To see an example of this scenario, you can run the following fix command:

```console
$ sudo pro fix USN-5079-2
```

The command will prompt you for a response, like this:

```
USN-5079-2: curl vulnerabilities
Found CVEs:
https://ubuntu.com/security/CVE-2021-22946
https://ubuntu.com/security/CVE-2021-22947

Fixing requested USN-5079-2
1 affected package is installed: curl
(1/1) curl:
A fix is available in Ubuntu Pro: ESM Infra.
The update is not installed because this system is not attached to a
subscription.

Choose: [S]ubscribe at ubuntu.com [A]ttach existing token [C]ancel
> 
```

You can see that the prompt is asking for an Ubuntu Pro subscription token. Any
user with a Ubuntu One account is entitled to a free personal token to use with
Ubuntu Pro. 

If you choose the `Subscribe` option on the prompt, the command
will ask you to go to the
[Ubuntu Pro portal](https://ubuntu.com/pro/). In the portal, you can get a free
subscription token by logging in with your "Single Sign On" (SSO) credentials;
the same credentials you use to log into https://login.ubuntu.com.

After getting your Ubuntu Pro token, you can hit <kbd>Enter</kbd> on the prompt
and it will ask you to provide the token you just obtained. After entering the
token you should now see the following output:

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

Found related USNs:
- USN-5079-1

Fixing related USNs:
- USN-5079-1
No affected source packages are installed.

✔ USN-5079-1 does not affect your system.

Summary:
✔ USN-5079-2 [requested] is resolved.
✔ USN-5079-1 [related] does not affect your system.
```

We can see that this command also fixed related USN **USN-5079-1**.
If you want to learn more about related USNs, refer to [our explanation guide](../explanations/cves_and_usns_explained.md#what-are-related-usns)

Finally, we can see that that the attach command was successful, which can be verified
by the status output we see when executing the command. Additionally, we can
observe that the USN is indeed fixed, which you can confirm by running the
`pro fix` command again:

```
USN-5079-2: curl vulnerabilities
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
Even though we are not covering this scenario here, if you have an expired
contract, `pro fix` will detect that and prompt you to attach a new token for
your machine.
```

## CVE/USN that require a Ubuntu Pro service

Now, let's assume that you have attached to an Ubuntu Pro subscription, but
when running `pro fix`, the required service that fixes the issue is not
enabled. In that situation, `pro fix` will also prompt you to enable that
service.

To confirm that, run the following command to disable `esm-infra`:

```console
$ sudo pro disable esm-infra
```

Now, you can run the following command:

```console
$ sudo pro fix CVE-2021-44731
```

And you should see the following output (if you type `E` when
prompted):

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

You can observe that the required service was enabled and `pro fix` was able to
successfully upgrade the affected package.

## CVE/USN that require a reboot

When running the `pro fix` command, sometimes we can install a package that
requires a system reboot to complete. The `pro fix` command can detect that and
will inform you about it.

You can confirm this by running the following fix command:

```console
$ sudo pro fix CVE-2022-0778
```

Then you will see the following output:

```
CVE-2022-0778: OpenSSL vulnerability
https://ubuntu.com/security/CVE-2022-0778

1 affected package is installed: openssl
(1/1) openssl:
A fix is available in Ubuntu Pro: ESM Infra.
{ apt update && apt install --only-upgrade -y libssl1.0.0 openssl }
A reboot is required to complete fix operation.

✘ CVE-2022-0778 is not resolved.
```

If we reboot the machine and run the command again, you will see that it is
indeed fixed:

```
CVE-2022-0778: OpenSSL vulnerability
https://ubuntu.com/security/CVE-2022-0778

1 affected package is installed: openssl
(1/1) openssl:
A fix is available in Ubuntu Pro: ESM Infra.
The update is already installed.

✔ CVE-2022-0778 is resolved.
```

## Partially resolved CVE/USN

Finally, you might run a `pro fix` command that only fixes some of the packages
affected. This happens when only a subset of the packages have available updates
to fix for that CVE/USN.

In this case, `pro fix` will tell you which package(s) it can or cannot fix.
But first, let's install a package so we can run `pro fix` to demonstrate this
scenario.

```console
$ sudo apt-get install expat=2.1.0-7 swish-e matanza ghostscript
```

Now, you can run the following command:

```console
$ sudo pro fix CVE-2017-9233
```

And you will see the following output:

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

We can see that two packages, `matanza` and `swish-e`, don't have any fixes
available, but there is one for `expat`. So, we install the fix for `expat` and
at the end of the report we can see that some packages are still affected.

As before, we can also observe that in this scenario we mark the CVE/USN as not
resolved.

## Close down the VM

Congratulations! You successfully ran a Multipass VM and used it to encounter
and resolve the main scenarios that you might find when you run `pro fix`.

When you are finished and want to leave the tutorial, you can shut down the VM
by first pressing <kbd>CTRL</kbd>+<kbd>D</kbd> to exit it, and then running the
following commands to delete the VM completely:

```console
$ multipass delete dev-x
$ multipass purge
```

## Next steps

We have successfully encountered and resolved the main scenarios that you might
find when you run `pro fix`.

If you need more information about this command, please feel free to reach out
to the Ubuntu Pro Client team on `#ubuntu-server` on
[Libera IRC](https://kiwiirc.com/nextclient/irc.libera.chat/ubuntu-server) --
we're happy to help! 

Alternatively, if you have a GitHub account, click on the "Have a question?"
link at the top of this page to leave us a message. We'd love to hear from you!
