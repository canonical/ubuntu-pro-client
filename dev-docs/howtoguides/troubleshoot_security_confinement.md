# How to troubleshoot apt_news security confinement

The `apt-news` service uses two types of security confinements:
  - [systemd sandboxing features](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html#Sandboxing)
  - [AppArmor profile](https://ubuntu.com/server/docs/security-apparmor)

In the git repository, these are located at:
  - [apt-news.service](https://github.com/canonical/ubuntu-pro-client/blob/main/systemd/apt-news.service)
  - `debian/apparmor/ubuntu_pro_apt_news.jinja2`

These security features restrict what the service can do on the system, and it's quite common that an application faced with unexpected "permission denied" errors, or unavailability of resources, will either crash or behave unexpectedly.

If you suspect the security confinement might be impacting the `apt-news` service, here are some troubleshooting tips.

## Panic: disable everything

To completely remove the security features and make sure they are or are not the cause of the problem you are troubleshooting, do the following:

1. Edit `/lib/systemd/system/apt-news.service` and remove or comment the `AppArmorProfile` line, and the security isolation lines. Here is what the minimal version of that file should look like:
```
  [Unit]
  Description=Update APT News

  [Service]
  Type=oneshot
  ExecStart=/usr/bin/python3 /usr/lib/ubuntu-advantage/apt_news.py
```

An alternative to removing `AppArmorProfile` from the unit file is to just disable it on the system, or put it in complain mode. See "Troubleshooting Apparmor" below for details.

2. Reload the systemd units:

```
  sudo systemctl daemon-reload
```

3. Use the service and observe if the problem you are troubleshooting is still there. If it's still there, then the security features are not the cause.



## Troubleshooting Apparmor

The Apparmor profile for the `apt-news` service is loaded via the `AppArmorProfile` directive in the unit file `/lib/systemd/system/apt-news.service`:
```
  [Service]
  ...
  AppArmorProfile=ubuntu_pro_apt_news
```

This will apply the specified AppArmor profile on service startup. If the profile does not exist, the service startup will fail. The actual profile is located in `/etc/apparmor.d/ubuntu_pro_apt_news`, and is loaded into the kernel at package install/upgrade time, or when the system boots.

To verify if the Apparmor profile is causing the issues you are observing, the first troubleshooting attempt should be to put it in "complain" mode. In that mode, it will allow everything, but log if something would have been blocked had the profile been in "enforce" mode.

To place the profile in complain mode, first install the `apparmor-utils` package, if it's not installed already:
```
  sudo apt install apparmor-utils
```

Then run this command:
```
  sudo aa-complain /etc/apparmor.d/ubuntu_pro_apt_news
```

This will both change the profile file to include the `complain` flag, and reload it into the kernel.

Next, keep an eye on the `dmesg` output with something like this:
```
sudo dmesg -wT | grep -E 'apparmor=\".*(profile=\"ubuntu_pro_|name=\"ubuntu_pro_)'
```

And exercise the service. For example, to be sure it will run, first remove some files:
```
sudo rm -rf /var/lib/apt/periodic/update-success-stamp /run/ubuntu-advantage /var/lib/ubuntu-advantage/messages/*
```

And then start the service:
```
sudo systemctl start apt-news.service
```

If you see any logs with `ALLOWED` in them, then that action is something that would have been blocked by the AppArmor profile had it not been in "complain" mode, and is something you should add to the AppArmor profile.

To make changes to the AppArmor profile, edit the `/etc/apparmor.d/ubuntu_pro_apt_news` file, save, and reload the profile with the following command:
```
sudo apparmor_parser -r -W -T /etc/apparmor.d/ubuntu_pro_apt_news
```

Explaining the full syntax of the AppArmor profiles is out of scope for this document. You can find more information in the [apparmor.d manpage](https://manpages.ubuntu.com/manpages/noble/man5/apparmor.d.5.html). The Ubuntu Server Guide also has a good introduction on the topic in the [Security - AppArmor](https://ubuntu.com/server/docs/security-apparmor) page.

ATTENTION: be mindful of the differences in Ubuntu Releases regarding the AppArmor profile syntax!


## Troubleshooting systemd sandboxing

Troubleshooting systemd sandboxing is not as straightforward as with AppArmor, because there are no specific logs telling you that a certain action was blocked. It will just be blocked, and it's up to the application to handle it. There is no "system" log to help with troubleshooting the sandbox rules.

The only way to troubleshoot this sandboxing is to methodically disable rule by rule in the `apt-news.service` file and test the service.

For example, let's take the `/lib/systemd/system/apt-news.service` unit file as below:
```
[Unit]
Description=Update APT News

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/lib/ubuntu-advantage/apt_news.py
AppArmorProfile=ubuntu_pro_apt_news
CapabilityBoundingSet=~CAP_SYS_ADMIN
CapabilityBoundingSet=~CAP_NET_ADMIN
CapabilityBoundingSet=~CAP_NET_BIND_SERVICE
CapabilityBoundingSet=~CAP_SYS_PTRACE
CapabilityBoundingSet=~CAP_NET_RAW
PrivateTmp=true
RestrictAddressFamilies=~AF_NETLINK
RestrictAddressFamilies=~AF_PACKET
```

If you suspect that the `PrivateTmp` restriction is causing problems, comment it:
```
...
CapabilityBoundingSet=~CAP_NET_RAW
#PrivateTmp=true
RestrictAddressFamilies=~AF_NETLINK
...
```

Then reload the unit files:
```
sudo systemctl daemon-reload
```

And try the service again:
```
sudo rm -rf /var/lib/apt/periodic/update-success-stamp /run/ubuntu-advantage /var/lib/ubuntu-advantage/messages/*
sudo systemctl start apt-news.service
```

If whatever incorrect behavior that you were observing is now gone, then it's likely that that restriction was causing it.

The exact meaning of each sandboxing feature is well documented upstream, in the [systemd.exec sandboxing](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html#Sandboxing) section of the manpage. But as with AppArmor, be mindful of differences between Ubuntu Releases: not all features from the latest releases will be available in, say, Ubuntu Xenial, for example.

There is one additional troubleshooting tip that can be helpful, and that is to run any command with specific sandboxing features enabled.

For example, let's try the `PrivateTmp` feature. First, let's create a file in `/tmp`:
```
touch /tmp/my-file
```

It should be visible to you. Let's check with `ls -la /tmp/my-file`:
```
-rw-r--r-- 1 root root 0 jan  3 16:31 /tmp/my-file
```

Now let's try it with the `PrivateTmp` restriction disabled, first. The command is:
```
systemd-run -qt -p PrivateTmp=no ls -la /tmp/my-file
```

And the output will be:
```
-rw-r--r-- 1 root root 0 jan  3 16:31 /tmp/my-file
```

What happens if we enable the restriction? The command now is:
```
systemd-run -qt -p PrivateTmp=yes ls -la /tmp/my-file
```

And we get:
```
/usr/bin/ls: cannot access '/tmp/my-file': No such file or directory
```

Interesting! What if we create a file in `/tmp` with the restriction enabled, will it still be there once the command finishes? Let's try:
```
systemd-run -qt -p PrivateTmp=yes touch /tmp/other-file
```

And when we check with `ls -la /tmp/other-file`:
```
ls: cannot access '/tmp/other-file': No such file or directory
```

That's what `PrivateTmp=yes` means: the service will get a fresh and empty `/tmp` directory when it starts, and that will be gone when it finishes.

These restrictions can be specified multiple times in the `systemd-run` command line with the `-p` parameter.

Here is another example: let's block the `CAP_NET_RAW` capability, and try the `ping` command:
```
systemd-run -qt -p CapabilityBoundingSet=~CAP_NET_RAW ping -c 1 1.1.1.1
```

That will show nothing, but the exit status `$?` is `203`, so something failed. If we check the journal, we will see:
```
jan 03 16:36:31 nsnx2 systemd[1]: Started run-u3002.service - /usr/bin/ping -c 1 1.1.1.1.
jan 03 16:36:31 nsnx2 (ping)[575067]: run-u3002.service: Failed to execute /usr/bin/ping: Operation not permitted
jan 03 16:36:31 nsnx2 (ping)[575067]: run-u3002.service: Failed at step EXEC spawning /usr/bin/ping: Operation not permitted
jan 03 16:36:31 nsnx2 systemd[1]: run-u3002.service: Main process exited, code=exited, status=203/EXEC
jan 03 16:36:31 nsnx2 systemd[1]: run-u3002.service: Failed with result 'exit-code'.
```


## Cheat sheet

Here are a few handful AppArmor and systemd tips.

| What                                    | How                                    |
|-----------------------------------------|----------------------------------------|
| Reload an AppArmor profile from disk    | `sudo apparmor_parser -r -W -T <file>` |
| Place a profile in complain mode        | `sudo aa-complain <file>`              |
| Place a profile in enforce mode         | `sudo aa-enforce <file>`               |
| List loaded profiles                    | `sudo aa-status`                       |
| Check AppArmor logs                     | `sudo dmesg -wT \| grep apparmor=`     |
| Run a command under an AppArmor profile | `sudo aa-exec -p <profile> <cmd>`      |
| Run a command with a systemd sanboxing property | `sudo systemd-run -qt -p <property> <cmd>` |
