# How to customise a cloud Ubuntu Pro image with FIPS updates

## Launch an Ubuntu Pro instance on your cloud

See the following links for up to date information for each supported cloud:

* https://ubuntu.com/aws/pro
* https://ubuntu.com/azure/pro
* https://ubuntu.com/gcp/pro

## Enable FIPS updates

Wait for the standard Ubuntu Pro services to be set up:

```bash
sudo pro status --wait
```

Use [the `enable` command](../howtoguides/enable_fips.md) to set up
FIPS updates.

```bash
sudo pro enable fips-updates --assume-yes
```

Now, reboot the instance:

```bash
sudo reboot
```

And verify that `fips-updates` is enabled in the output of `pro status`:
```bash
sudo pro status
```

Also remove the `machine-id` so that it is regenerated for each instance
launched from the snapshot.

```bash
sudo rm /etc/machine-id
```

## Snapshot the instance as a Cloud image

Cloud-specific instructions are here:

* [AWS](https://docs.aws.amazon.com/toolkit-for-visual-studio/latest/user-guide/tkv-create-ami-from-instance.html)
* [Azure](https://docs.microsoft.com/en-us/azure/virtual-machines/windows/capture-image-resource)
* [GCP](https://cloud.google.com/compute/docs/machine-images/create-machine-images)

## Launch your custom image

Use your specific cloud to launch a new instance from the custom image.

````{note}
For versions of the Ubuntu Pro Client prior to 27.11, you will need to re-enable `fips-updates` on each
instance launched from the custom image.

This won't require a reboot and is only necessary to ensure the instance gets
updates to FIPS packages when they become available.

```bash
sudo pro enable fips-updates --assume-yes
```

This can be scripted using [cloud-init user data](https://cloudinit.readthedocs.io/en/latest/topics/modules.html#runcmd) at launch time:
```yaml
#cloud-config
# Enable fips-updates after pro auto-attach and reboot after cloud-init completes
runcmd:
  - 'pro status --wait'
  - 'pro enable fips-updates --assume-yes'
```

````