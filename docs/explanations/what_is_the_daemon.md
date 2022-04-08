# What is the Pro Upgrade Daemon?

UA client sets up a daemon on supported platforms (currently GCP only) to detect if an Ubuntu Pro license is purchased for the machine. If a Pro license is detected, then the machine is automatically attached.

If you are uninterested in UA services, you can safely stop and disable the daemon using systemctl:

```
sudo systemctl stop ubuntu-advantage.service
sudo systemctl disable ubuntu-advantage.service
```
