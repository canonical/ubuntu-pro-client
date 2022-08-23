# Status output explanation

When running `ua status` we can observe two different types of outputs, attached vs unattached.
When unattached, users will see the status table containing only three columns:

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

* **SERVICE**: is the name of service being offered
* **AVAILABLE**: if that service is available on that machine. To verify if a service is available, we
  check the machine kernel version, architecture and Ubuntu release it is running.
* **DESCRIPTION**: A short description of the service.

However, if we run the same command when attached, we have an output with 4 columns:

```
SERVICE       ENTITLED  STATUS    DESCRIPTION
cis           yes       disabled  Center for Internet Security Audit Tools
esm-infra     yes       enabled   Expanded Security Maintenance for Infrastructure
fips          yes       n/a       NIST-certified core packages
fips-updates  yes       n/a       NIST-certified core packages with priority security updates
livepatch     yes       n/a       Canonical Livepatch service
``` 

Here we can notice that the column **AVAILABLE** no longer applies and we have new columns:

* **ENTITLED**: If the user subscription allow that service to be enabled
* **STATUS**: The state of that service on the machine.

It is possible that a service appears as available when running status unattached, but turns
out as not entitled. This happens because even if the service can be enabled on the machine,
if your UA subscription doesn't allow you to do that, UA cannot enable it.

Additionally, the **STATUS** column allows for three possible states:

* **enabled**: service is enabled in the machine
* **disabled**: service is not currently running
* **n/a**: This means non-applicable. This can happen if the service cannot be enabled on the machine
  due to a non-contract restriction. For example, we cannot enable `livepatch` on a container.

### Notices
Notices are information regarding the UA status which either require some kind of action from the user, or may impact the experience with UA.

For example, let's say FIPS was just enabled, but the system wasn't rebooted yet (which is needed for booting into the FIPS Kernel), the output of `ua status`  will contain:
```bash
NOTICES
FIPS support requires system reboot to complete configuration.
```
After the system is rebooted, the notice will go away.

Notices can always be resolved, and the way to resolve it should be explicit in the notice itself.

### Features
Features are extra configuration values that can be set/unset in `uaclient.conf`. Most of those are meant for development/testing purposes, but some can be used in fome application flows. For example, to always have beta services with the same flow as the non-beta (for enable, status, etc), `uaclient.conf` may have:
```
features:
  allow_beta: True
```
In this case, the output of `ua status` will contain:
```bash
FEATURES
+allow_beta
```

Keep in mind that any feature defined like this will be listed, even if it is invalid or typed the wrong way. Those appear on status for information/debugging purposes.
