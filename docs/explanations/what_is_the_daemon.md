# What is the Pro upgrade daemon?

Ubuntu Pro Client sets up a daemon on supported platforms (currently GCP
only) to detect if an Ubuntu Pro license has been purchased for the machine.
If a Pro license is detected, then the machine is automatically attached.

If you are not interested in Ubuntu Pro services and don't want your machine to
be automatically attached to your subscription, you can safely stop and disable
the daemon using `systemctl`:

```
sudo systemctl stop ubuntu-advantage.service
sudo systemctl disable ubuntu-advantage.service
```
