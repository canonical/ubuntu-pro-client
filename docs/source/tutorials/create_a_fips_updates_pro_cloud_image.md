# Create a customized Cloud Ubuntu Pro image with FIPS Updates

## Step 1: Launch an Ubuntu Pro instance on your cloud

See the following links for up to date information for each supported cloud:
* https://ubuntu.com/aws/pro
* https://ubuntu.com/azure/pro
* https://ubuntu.com/gcp/pro

## Step 2: Enable FIPS Updates

First wait for the standard Ubuntu Pro services to be set up.

```bash
sudo ua status --wait
```

Then use [the enable command](../howtoguides/enable_fips.md) to setup FIPS Updates.
```bash
sudo ua enable fips-updates --assume-yes
```

Now reboot the instance
```bash
sudo reboot
```

And verify that `fips-updates` is enabled in the output of `ua status`
```bash
sudo ua status
```

Also remove the machine-id so that it is regenerated for each instance launch from the snapshot.
```bash
sudo rm /etc/machine-id
```

## Step 3: Snapshot the instance as a cloud image

Cloud-specific instructions are here:
* [AWS](https://docs.aws.amazon.com/toolkit-for-visual-studio/latest/user-guide/tkv-create-ami-from-instance.html)
* [Azure](https://docs.microsoft.com/en-us/azure/virtual-machines/windows/capture-image-resource)
* [GCP](https://cloud.google.com/compute/docs/machine-images/create-machine-images)

## Step 4: Launch your custom image!

Use your specific cloud to launch a new instance from your custom image.

> **Note**
> For versions prior to 27.11, you will need to re-enable fips-updates on each instance that is launched from the custom image.
>
> This won't require a reboot and is only necessary to ensure the instance gets updates to fips packages when they become available.
>
> ```bash
> sudo ua enable fips-updates --assume-yes
> ```
>
> You can easily script this using [cloud-init user-data](https://cloudinit.readthedocs.io/en/latest/topics/modules.html#runcmd) at launch time
> ```yaml
> #cloud-config
> # Enable fips-updates after pro auto-attach and reboot after cloud-init completes
> runcmd:
>   - 'ua status --wait'
>   - 'ua enable fips-updates --assume-yes'
> ```
