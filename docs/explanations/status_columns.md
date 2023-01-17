# The `pro status` output explained

When running `pro status` we can observe two different types of outputs, which
depend on whether the Ubuntu Pro subscription is attached or unattached.

## Pro subscription unattached
When unattached, users will see the following status table containing only
three columns:

```
SERVICE          AVAILABLE  DESCRIPTION
cc-eal           no         Common Criteria EAL2 Provisioning Packages
cis              no         Security compliance and audit tools
esm-infra        yes        Expanded Security Maintenance for Infrastructure
fips             no         NIST-certified core packages
fips-updates     no         NIST-certified core packages with priority security updates
livepatch        yes        Canonical Livepatch service
```

Where:

* **SERVICE**: Is the name of service being offered
* **AVAILABLE**: Shows if that service is available on that machine. To verify
  if a service is available, we check the machine kernel version, architecture,
  Ubuntu release being used and the machine type (i.e lxd for LXD containers)
* **DESCRIPTION**: A short description of the service.

## With Pro subscription attached

However, if we run the same command when attached, we have an output with 4
columns:

```
SERVICE       ENTITLED  STATUS    DESCRIPTION
cis           yes       disabled  Center for Internet Security Audit Tools
esm-infra     yes       enabled   Expanded Security Maintenance for Infrastructure
fips          yes       n/a       NIST-certified core packages
fips-updates  yes       n/a       NIST-certified core packages with priority security updates
livepatch     yes       n/a       Canonical Livepatch service
```

You may notice that the column **AVAILABLE** is no longer shown, and instead we
see the following new columns:

* **ENTITLED**: Shows if the user subscription allows that service to be
  enabled.
* **STATUS**: Reports the state of that service on the machine.

It is possible that a service could appear as "available" when the Pro status is
unattached, but then shows as "not entitled" if the subscription is later
attached. This happens because even if the service is available, if your Ubuntu
Pro subscription doesn't allow you access to a service, `pro` cannot enable it.

The **STATUS** column allows for three possible states:

* **enabled**: The service is enabled on the machine.
* **disabled**: The service is not currently running.
* **n/a**: This means "not applicable". This will show if the service cannot be
  enabled on the machine due to a non-contract restriction. For example, we
  cannot enable `livepatch` on a container.

## Notices

"Notices" are information regarding the Ubuntu Pro status which either require
some kind of action from the user, or may impact the experience with Ubuntu Pro.

For example, let's say FIPS was just enabled, but the system wasn't rebooted
yet (which is required for booting into the FIPS Kernel). The output of
`pro status` in this case will contain:

```
NOTICES
FIPS support requires system reboot to complete configuration.
```

After the system is rebooted, the notice will go away.

Notices can always be resolved, and the instructions on how to resolve it will
be explicitly stated in the notice itself.

## Features

"Features" are extra configuration values that can be set and unset in
`uaclient.conf`. Most of these are meant for development/testing purposes, but
some can be used in application flows. For example, to always have beta services
with the same flow as the non-beta (for `enable`, `status`, etc.),
`uaclient.conf` may have:

```
features:
  allow_beta: true
```

In this case, the output of `pro status` will contain:

```
FEATURES
allow_beta: True
```

It's important to keep in mind that any feature defined like this will be
listed, even if it is invalid or typed the wrong way. Those appear in `status`
output for informational and debugging purposes.
