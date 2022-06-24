# How to get UA token and attach to a subscription

Retrieve your UA token from the [advantage](https://ubuntu.com/advantage/) portal. You will log in with your SSO credentials, the same credentials you use for https://login.ubuntu.com. Note that you
can obtain a free personal token, which already provide you with access to several of the UA
services.

Once that token is obtained, to attach your machine to a subscription, just run:

```
$ sudo ua attach YOUR_TOKEN
```

You should see output like the following, indicating that you have successfully associated this
machine with your account.

```
Enabling default service esm-infra
Updating package lists
ESM Infra enabled
This machine is now attached to 'UA Infra - Essential (Virtual)'

SERVICE       ENTITLED  STATUS    DESCRIPTION
cis           yes       disabled  Center for Internet Security Audit Tools
esm-infra     yes       enabled   Extended Security Maintenance for Infrastructure
fips          yes       n/a       NIST-certified FIPS modules
fips-updates  yes       n/a       Uncertified security updates to FIPS modules
livepatch     yes       n/a       Canonical Livepatch service

NOTICES
Operation in progress: ua attach

Enable services with: ua enable <service>
```

Once the UA client is attached to your UA account, you can use it to activate various services,
including: access to ESM packages, Livepatch, FIPS, and CIS. Some features are specific to certain
LTS releases
