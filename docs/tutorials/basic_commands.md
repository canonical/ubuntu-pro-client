# Get started with Ubuntu Pro Client

The Ubuntu Pro Client (`pro`) provides a simple mechanism for viewing, enabling
and disabling offerings from Canonical on your system. In this tutorial we will
cover the base `pro` commands that help you to successfully manage the offering
on your machine.

## Main `pro` commands

When dealing with `pro` through the command line, there are six commands that
cover the main functionalites of the tool. They are:

* `status`
* `attach`
* `refresh`
* `detach`
* `enable`
* `disable`

In this tutorial, we will go through all these commands and learn how to
properly use them. To achieve this without making any modifications to your
machine, we will use a Xenial Multipass VM.

We have chosen [Multipass](https://multipass.run/) for this tutorial because it
allows us to easily launch VMs without the need for any complicated setup.

## How to use this tutorial

The commands in each code block can be copied and pasted directly into your
terminal. You can use the "copy code" button to the right-hand side of the block
and this will copy the code for you (without the command prompt!).

## Install Multipass

To install Multipass on your computer, please run the following command on your
machine:

```console
$ sudo snap install multipass
```

## Create the Xenial Multipass virtual machine

Now that we have installed Multipass, we can launch our Multipass VM by running
this command:

```console
$ multipass launch xenial --name dev-x
```

We can easily access our new VM by running:

```console
$ multipass shell dev-x
```

Notice that when you run this command, your terminal username and hostname
change to:

```
ubuntu@dev-x
```

This indicates that you are now inside the VM.

Finally, let's run `apt update` and `apt upgrade` on the VM to make sure we are
operating on the correct version:

```console
$ sudo apt update && sudo apt upgrade -y
```

## Base `pro` commands

### `status`

The `status` command of `pro` will show you the status of any Ubuntu Pro
service on your machine. It also helps you to easily verify that your machine is
attached to an Ubuntu Pro subscription.

Let's run it on our VM:

```console
$ pro status
```

You can expect to see an output similar to this:

```
SERVICE       AVAILABLE  DESCRIPTION
cis           yes        Center for Internet Security Audit Tools
esm-infra     yes        Expanded Security Maintenance for Infrastructure
fips          yes        NIST-certified core packages
fips-updates  yes        NIST-certified core packages with priority security updates
livepatch     yes        Canonical Livepatch service

This machine is not attached to an Ubuntu Pro subscription.
See https://ubuntu.com/pro
```

You can see that the `status` command shows the services available to your
machine, while also presenting a short description for each service.

If you also look at the last lines of the output, you can see that this machine
is not currently attached to an Ubuntu Pro subscription.

```
This machine is not attached to an Ubuntu Pro subscription.
See https://ubuntu.com/pro
```

### `attach`

We have seen which service offerings are available to us, but to access them we
first need to attach an Ubuntu Pro subscription. We can do this by running the
`attach` command.

Before you run this command, you will need to get your Ubuntu Pro token. Any
user with an Ubuntu One account is entitled to a free personal token to use
with Ubuntu Pro.

You can retrieve your Ubuntu Pro token from the
[Ubuntu Pro portal](https://ubuntu.com/pro/). Log in with your "single sign on"
(SSO) credentials -- the same credentials you use for https://login.ubuntu.com.
Copy your Ubuntu Pro token, then go to the VM and run:

```console
$ sudo pro attach YOUR_TOKEN
```

You should then see output similar to this:

```
Enabling default service esm-infra
Updating package lists
Ubuntu Pro: ESM Infra enabled
This machine is now attached to 'USER ACCOUNT'

SERVICE       ENTITLED  STATUS    DESCRIPTION
cis           yes       disabled  Center for Internet Security Audit Tools
esm-infra     yes       enabled   Expanded Security Maintenance for Infrastructure
fips          yes       n/a       NIST-certified core packages
fips-updates  yes       n/a       NIST-certified core packages with priority security updates
livepatch     yes       n/a       Canonical Livepatch service

NOTICES
Operation in progress: pro attach

Enable services with: pro enable <service>

                Account: USER ACCOUNT
           Subscription: USER SUBSCRIPTION
            Valid until: 9999-12-31 00:00:00+00:00
Technical support level: essential
```

From this output, you can see that the `attach` command has introduced the
"status" column. This shows which services (specified by your user
subscription) have been enabled by default.

After the command ends, `pro` displays the new state of the machine. This status
output is exactly what you see if you run the `status` command. Let's confirm
this by running the `status` command again:

```console
$ pro status
```

```{seealso}
You may be wondering why the output of `status` is different depending on
whether `pro` is attached or unattached. For more information on why this is,
please refer to our
[explanation on the different columns](../explanations/status_columns.md).
```

Finally, another useful bit at the end of the output for both `attach` and
`status` is the contract expiration date:

```
    Account: USER ACCOUNT
Subscription: USER SUBSCRIPTION
Valid until: 9999-12-31 00:00:00+00:00
```

The `Valid until` field describes when your contract will expire, so you can be
aware of when it needs to be renewed.

### `refresh`

Although *free* tokens never expire, if you buy an Ubuntu Pro subscription and
later need to renew your contract, how can you make your machine aware of it?

This is where the `refresh` command comes in:

```console
$ sudo pro refresh
```

This command will "refresh" the contract on your machine. It's also really
useful if you want to change any definitions on your subscription. 

For example, let's assume that you now want `cis` to be enabled by default when
attaching. After you modify your subscription on the Ubuntu Pro website to
enable it by default, running the refresh command will process the changes you
made, and `cis` will then be enabled.

```{hint}
The `refresh` command does more than just update the contract in the machine.
If you would like more information about the command, please take a look at
[this deeper explanation](../explanations/what_refresh_does.md).
```

### `enable`

There is another way to enable a service that wasn't activated during `attach`
or `refresh`. Let us suppose that you now want to enable `cis` on the machine
manually. To achieve this, you can use the `enable` command.

Let's try enabling `cis` on our VM by running:

```console
$ sudo pro enable cis
```

After running the command, you should see output similar to this:

```
One moment, checking your subscription first
Updating package lists
Installing CIS Audit packages
CIS Audit enabled
Visit https://security-certs.docs.ubuntu.com/en/cis to learn how to use CIS
```

We can then confirm that `cis` is now enabled by using the `status` command
again:

```console
$ pro status
```

And you should see:
```
SERVICE       ENTITLED  STATUS    DESCRIPTION
cis           yes       enabled   Center for Internet Security Audit Tools
esm-infra     yes       enabled   Expanded Security Maintenance for Infrastructure
fips          yes       n/a       NIST-certified core packages
fips-updates  yes       n/a       NIST-certified core packages with priority security updates
livepatch     yes       n/a       Canonical Livepatch service
```

You can see now that `cis` is marked as `enabled` under 'status'.


### `disable`

What happens if you don't want a service anymore? You can very simply disable
any service offering through `pro`. For example, let's disable the `cis`
service we just enabled by running `disable` on our VM:

```console
$ sudo pro disable cis
```

Let's now run `pro status` to see what happened to `cis`:

```
SERVICE       ENTITLED  STATUS    DESCRIPTION
cis           yes       disabled  Center for Internet Security Audit Tools
esm-infra     yes       enabled   Expanded Security Maintenance for Infrastructure
fips          yes       n/a       NIST-certified core packages
fips-updates  yes       n/a       NIST-certified core packages with priority security updates
livepatch     yes       n/a       Canonical Livepatch service
```

You can see that `cis` status is back to being disabled.

```{important}
The `disable` command doesn't uninstall any package that was installed by
the service, or undo any configuration that was applied to the machine -- it
only removes the access you have to the service.
```

### `detach`

Finally, what if you decide you no longer want this machine to be attached to an
Ubuntu Pro subscription? To disable all of the Ubuntu Pro services and remove
the subscription you stored on your machine during attach, you can use the
`detach` command:

```console
$ sudo pro detach
```

Just like the `disable` command, `detach` will also not uninstall any packages
that were installed by any of the services enabled through `pro`.


## Close down the VM

Congratulations! You successfully ran a Multipass VM and used it to try out the
six main commands of the Ubuntu Pro Client.

If you want to continue testing the different features and functions of `pro`,
you can run the command:

```
$ pro help
```

This will provide you with a full list of all the commands available, and
details of how to use them. Feel free to play around with them in your VM and
see what else `pro` can do for you!

When you are finished and want to leave the tutorial, you can shut down the VM
by first pressing <kbd>CTRL</kbd>+<kbd>D</kbd> to exit it, and then running the
following commands to delete the VM completely:

```console
$ multipass delete dev-x
$ multipass purge
```

## Next steps

If you would now like to see some more advanced options to configure `pro`,
we recommending taking a look at our [how-to guides](../howtoguides).

If you have any questions or need some help, please feel free to reach out to
the `pro` team on `#ubuntu-server` on
[Libera IRC](https://kiwiirc.com/nextclient/irc.libera.chat/ubuntu-server) --
we're happy to help! 

Alternatively, if you have a GitHub account, click on the "Have a question?"
link at the top of this page to leave us a message. We'd love to hear from you!
