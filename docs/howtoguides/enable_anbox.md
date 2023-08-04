# How to enable Anbox Cloud

```{important}
[Anbox Cloud is supported on 20.04 and 22.04 releases](https://anbox-cloud.io/).
```

To use Anbox, you will need to enable it directly throught the Ubuntu Pro Client,
which will install all of the necessary snaps and set up the APT sources needed for
the service.

## Make sure `pro` is up-to-date

All systems come with `pro` pre-installed through the `ubuntu-advantage-tools`
package. To make sure that you're running the latest version of `pro`, run the
following commands:

```console
sudo apt update && sudo apt install ubuntu-advantage-tools
```

## Enable Anbox

To enable Anbox Cloud, run:

```console
$ sudo pro enable anbox-cloud
```

```{important}
The Anbox Cloud service can only be installed on containers using the `--access-only` flag.
This option will only set up the APT sources for Anbox, but not install any of the snaps.
```

You should see output like the following, indicating that Anbox Cloud
was correctly enabled on your system:

```
One moment, checking your subscription first
Installing required snaps
Installing required snap: amc
Installing required snap: anbox-cloud-appliance
Installing required snap: lxd
Updating package lists
Anbox Cloud enabled
To finish setting up the Anbox Cloud Appliance, run:

$ sudo anbox-cloud-appliance init

You can accept the default answers if you do not have any specific
configuration changes.
For more information, see https://anbox-cloud.io/docs/tut/installing-appliance
```

```{important}
Please note that the output states an additional step is required to
complete the Anbox Cloud setup
```

You can also confirm that the service is enabled by running the `pro status` command.
It should contain the following line for `anbox-cloud`:

```console
SERVICE          ENTITLED  STATUS    DESCRIPTION
anbox-cloud      yes       enabled   Scalable Android in the cloud   
```

## Disable the service

If you wish to disable Anbox, you can use the following command to
disable it:

```bash
sudo pro disable anbox-cloud
```

Note that this command will only remove the APT sources, but not uninstall the snaps.
