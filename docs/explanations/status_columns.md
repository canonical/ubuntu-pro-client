# Status output explanation

When running `ua status` we can observe two different types of outputs, attached vs unattached.
When unattached, users will see the status table containing only three columns:

```
SERVICE          AVAILABLE  DESCRIPTION
cc-eal           no         Common Criteria EAL2 Provisioning Packages
cis              no         Security compliance and audit tools
esm-infra        yes        UA Infra: Extended Security Maintenance (ESM)
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
esm-apps      yes       enabled   UA Apps: Extended Security Maintenance (ESM)
esm-infra     yes       enabled   UA Infra: Extended Security Maintenance (ESM)
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
