# How to get an Ubuntu Pro token and attach to a subscription

Retrieve your Ubuntu Pro token from the [Ubuntu Pro portal](https://ubuntu.com/pro/). You will
log in with your SSO credentials, the same credentials you use for https://login.ubuntu.com. Note that you
can obtain a free personal token, which provides you with access to several of the Ubuntu Pro
services.

Once that token is obtained, to attach your machine to a subscription, just run:

```
$ sudo pro attach YOUR_TOKEN
```

You should see output like the following, indicating that you have successfully associated this
machine with your account.

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

Once the Ubuntu Pro Client is attached to your Ubuntu Pro account, you can use it to activate various services,
including: access to ESM packages, Livepatch, FIPS, and CIS. Some features are specific to certain
LTS releases
