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

## Machine-readable output

The `pro status` command supports a `--format` flag with options including `json` and `yaml`. These result in a machine-readable form of the information presented by the `pro status` command.

```{note}
`pro status` should return the same results whether using `sudo` or not, but earlier versions did not always do this. We recommend using `sudo` whenever possible.
```

For example, running `sudo pro status --format=json` on an attached machine may give you something like this:
```javascript
{
  "_doc": "Content provided in json response is currently considered Experimental and may change",
  "_schema_version": "0.1",
  "account": {
    "created_at": "2000-01-02T03:04:05+06:00",
    "id": "account_id",
    "name": "Test"
  },
  "attached": true,
  "config": { ...effectiveConfiguration },
  "config_path": "/etc/ubuntu-advantage/uaclient.conf",
  "contract": {
    "created_at": "2000-01-02T03:04:05+06:00",
    "id": "contract_id",
    "name": "contract_name",
    "products": [ "uaa-essential" ],
    "tech_support_level": "essential"
  },
  "effective": null,
  "environment_vars": [...proClientEnvironmentVariables],
  "errors": [],
  "execution_details": "No Ubuntu Pro operations are running",
  "execution_status": "inactive",
  "expires": "9999-12-31T00:00:00+00:00",
  "features": {},
  "machine_id": "machine_id",
  "notices": [],
  "result": "success",
  "services": [
    {
      "available": "yes",
      "blocked_by": [],
      "description": "Expanded Security Maintenance for Applications",
      "description_override": null,
      "entitled": "yes",
      "name": "esm-apps",
      "status": "enabled",
      "status_details": "Ubuntu Pro: ESM Apps is active",
      "warning": null
    },
    {
      "available": "yes",
      "blocked_by": [],
      "description": "Expanded Security Maintenance for Infrastructure",
      "description_override": null,
      "entitled": "yes",
      "name": "esm-infra",
      "status": "enabled",
      "status_details": "Ubuntu Pro: ESM Infra is active",
      "warning": null
    },
    {
      "available": "yes",
      "blocked_by": [],
      "description": "Canonical Livepatch service",
      "description_override": null,
      "entitled": "yes",
      "name": "livepatch",
      "status": "enabled",
      "status_details": "",
      "warning": null
    },
    ...otherServiceStatusObjects
  ],
  "simulated": false,
  "version": "27.13.6~18.04.1",
  "warnings": []
}
```

Some particularly important attributes in the output include:
* `attached`: This boolean value indicates whether this machine is attached to an Ubuntu Pro account. This does not tell you if any particular service (e.g. `esm-infra`) is enabled. You must check the individual service item in the `services` list for that status (described below).
* `expires`: This is the date that the Ubuntu Pro subscription is valid until (in RFC3339 format). After this date has passed the machine should be treated as if not attached and no services are enabled. `attached` may still say `true` and services may still say they are `entitled` and `enabled`, but if the `expires` date has passed, you should assume the services are not functioning.
* `services`: This is a list of Ubuntu Pro services. Each item has its own attributes. Widely applicable services include those with `name` equal to `esm-infra`, `esm-apps`, and `livepatch`. Some important fields in each service object are:
  * `name`: The name of the service.
  * `entitled`: A boolean indicating whether the attached Ubuntu Pro account is allowed to enable this service.
  * `status`: A string indicating the service's current status on the machine. Any value other than `enabled` should be treated as if the service is not enabled and not working properly on the machine. Possible values are:
    * `enabled`: The service is enabled and working.
    * `disabled`: The service can be enabled but is not currently.
    * `n/a`: The service cannot be enabled on this machine.
    * `warning`: The service is supposed to be enabled but something is wrong. Check the `warning` field in the service item for additional information.

For example, if you want to programatically find the status of esm-infra on a particular machine, you can use the following command:
```shell
sudo pro status --format=json | jq '.services[] | select(.name == "esm-infra").status'
```
That command will print one of the `status` values defined above.

```{attention}
In an future version of Ubuntu Pro Client, there will be an [API](../references/api.rst) function to access this information. For now, though, `pro status --format=json` is the recommended machine-readable interface to this data.
```
