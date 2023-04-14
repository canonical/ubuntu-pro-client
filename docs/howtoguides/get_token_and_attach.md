# How to get an Ubuntu Pro token and attach to a subscription

## Get an Ubuntu Pro token

Retrieve your Ubuntu Pro token from the
[Ubuntu Pro portal](https://ubuntu.com/pro/). You will log in with your "Single
Sign On" credentials, the same credentials you use for https://login.ubuntu.com.

Being logged in you can then go to the
[Ubuntu Pro Dashboard](https://ubuntu.com/pro/dashboard) that is associated to
your user. It will show you all subscriptions currently available to you and
for each the associated token.

Note that even without buying anything you can always obtain a free personal
token that way, which provides you with access to several of the Ubuntu Pro
services.

## Attach to a subscription

Once that token is obtained, to attach your machine to a subscription, just run:

```
$ sudo pro attach YOUR_TOKEN
```

You should see output like the following, indicating that you have successfully
associated this machine with your account.

```
Enabling default service esm-infra
Updating package lists
ESM Infra enabled
This machine is now attached to 'Ubuntu Pro'

SERVICE       ENTITLED  STATUS    DESCRIPTION
esm-apps      yes       enabled   Expanded Security Maintenance for Applications
esm-infra     yes       enabled   Expanded Security Maintenance for Infrastructure
livepatch     yes       enabled   Canonical Livepatch service

NOTICES
Operation in progress: pro attach

Enable services with: pro enable <service>
```

Once the Ubuntu Pro Client is attached to your Ubuntu Pro account, you can use
it to activate various services, including: access to ESM packages, Livepatch,
FIPS, and CIS. Some features are specific to certain LTS releases.

## Control of auto-enabled services

Your subscription controls which services are available to you as shown and
controlled on the [Ubuntu Pro Dashboard](https://ubuntu.com/pro/dashboard).

Recommended services are auto-enabled when attaching a system. Which services
are considered recommended can, for some subscriptions, be controlled on the
[Ubuntu Pro Dashboard](https://ubuntu.com/pro/dashboard) by toggling those.

![Toggling recommended services in the Pro Dashboard](pro-dashboard-service-toggles.png)

In case you can not control your subscription (depends on the subscription type
and your users permissions related to it). Or if you do not want to change the
defaults, but you do not want to auto-enable anything while attaching a particular
machine you can always pass `--no-auto-enable` to `attach`, but not auto-enable
any services using the following command:

```
$ sudo pro attach YOUR_TOKEN --no-auto-enable
```
