# The Ubuntu Pro API reference guide

The Ubuntu Pro Client has a Python-based API to be consumed by users who want
to integrate the Client's functionality with their software.

The functions and objects are available through the `uaclient.api` module, and
all of the available endpoints return an object with specific data for the
calls.

Besides importing the Python code directly, consumers who are not writing
Python may use the command line interface (CLI) to call the same functionality,
using the `pro api` command. This command will always return a JSON with a
standard structure, as can be seen below:

```json
{
    "_schema_version": "v1",
    "data": {
        "attributes": {
            // <endpoint specific attributes>
        },
        "meta": {
            "environment_vars": []
        },
        "type": "<response_type>"
    },
    "errors": [], 
    "result": "<success|failure>",
    "version": "<client version>", 
    "warnings": []
}
```

## Version dependencies
The package name of Ubuntu Pro Client is `ubuntu-advantage-tools`.

The documentation for each endpoint below states the first version to include that endpoint.

If you depend on these endpoints, we recommend using a standard dependency version requirement to ensure that a sufficiently up-to-date version of the Pro Client is installed before trying to use it.

```{important}
The `~` at the end of the version is important to ensure that dpkg version comparison works as expected.
```

For example, if your software is packaged as a deb, then you can add the following to your `Depends` list in your `control` file to ensure the installed version is at least 27.11~:
```
ubuntu-advantage-tools (>= 27.11~)
```

### Runtime version detection
If you need to detect the current version at runtime, the most reliable way is to query `dpkg`.
```
dpkg-query --showformat='${Version}' --show ubuntu-advantage-tools
```

If you need to compare versions at runtime, make sure you use the `dpkg` version comparison algorithm.
For example, the following will exit 0 if the currently installed version of Pro Client is at least 27.11~:
```
dpkg --compare-versions "$(dpkg-query --showformat='${Version}' --show ubuntu-advantage-tools)" ge "27.11~"
```

### Runtime feature detection
As an alternative to version detection, you can use feature detection. This is easier to do when importing the API in python than it is when using the `pro api` subcommand.

In python, try to import the desired endpoint. If an `ImportError` is raised, then the currently installed version of Ubuntu Pro Client doesn't support that endpoint.

For example:
```python
try:
    from uaclient.api.u.pro.version.v1 import version
    pro_client_api_supported = True
except ImportError:
    pro_client_api_supported = False
```

You could do something similar by catching certain errors when using the `pro api` subcommand, but there are more cases that could indicate an old version, and it generally isn't recommended.


### Errors and Warnings fields

When using the API through the CLI, we use two distinct fields to list issues to the users; *errors*
and *warnings*. Both of those fields will contain a list of JSON objects explaining unexpected
behavior during the execution of a command. For example, the *errors* field will be populated like
this if we have a connectivity issue when running a `pro api` command:

```json
[
    {
        "msg": "Failed to connect to authentication server",
        "code": "connectivity-error",
        "meta": {}
    }
]
```

Finally, *warnings* follow the exact same structure as *errors*. The only difference is that
*warnings* means that the command was able to complete although unexpected scenarios happened
when executing the command.

## Available endpoints
The currently available endpoints are:
- [u.pro.version.v1](#uproversionv1)
- [u.pro.attach.magic.initiate.v1](#uproattachmagicinitiatev1)
- [u.pro.attach.magic.wait.v1](#uproattachmagicwaitv1)
- [u.pro.attach.magic.revoke.v1](#uproattachmagicrevokev1)
- [u.pro.attach.auto.should_auto_attach.v1](#uproattachautoshould_auto_attachv1)
- [u.pro.attach.auto.full_auto_attach.v1](#uproattachautofull_auto_attachv1)
- [u.pro.attach.auto.configure_retry_service.v1](#uproattachautoconfigure_retry_servicev1)
- [u.pro.security.status.livepatch_cves.v1](#uprosecuritystatuslivepatch_cvesv1)
- [u.pro.security.status.reboot_required.v1](#uprosecuritystatusreboot_requiredv1)
- [u.pro.packages.summary.v1](#upropackagessummaryv1)
- [u.pro.packages.updates.v1](#upropackagesupdatesv1)
- [u.pro.status.is_attached.v1](#uprostatusis_attachedv1)
- [u.pro.status.enabled_services.v1](#uprostatusenabled_servicesv1)
- [u.security.package_manifest.v1](#usecuritypackage_manifestv1)
- [u.unattended_upgrades.status.v1](#uunattended_upgradesstatusv1)

## u.pro.version.v1

Introduced in Ubuntu Pro Client Version: `27.11~`

Shows the installed Pro Client version.

### Args

This endpoint takes no arguments.

### Python API interaction

#### Calling from Python code

```python
from uaclient.api.u.pro.version.v1 import version

result = version()
```

#### Expected return object:

`uaclient.api.u.pro.version.v1.VersionResult`

|Field Name|Type|Description|
|-|-|-|
|`installed_version`|*str*|The current installed version|

### Raised exceptions

- `VersionError`: Raised if the Client cannot determine the version.

### CLI interaction

#### Calling from the CLI:

```bash
pro api u.pro.version.v1
```

#### Expected attributes in JSON structure

```json
{
    "installed_version":"<version>"
}
```

## u.pro.attach.magic.initiate.v1

Introduced in Ubuntu Pro Client Version: `27.11~`

Initiates the Magic Attach flow, retrieving the User Code to confirm the
operation and the Token used to proceed.

### Args

This endpoint takes no arguments.

### Python API interaction

#### Calling from Python code

```python
from uaclient.api.u.pro.attach.magic.initiate.v1 import initiate

result = initiate()
```

#### Expected return object:

`uaclient.api.u.pro.attach.magic.initiate.v1.MagicAttachInitiateResult`

|Field Name|Type|Description|
|-|-|-|
|`user_code`|*str*|Code the user will see in the UI when confirming the Magic Attach|
|`token`|*str*|Magic Token used by the tooling to continue the operation|
|`expires`|*str*|Timestamp of the Magic Attach process expiration|
|`expires_in`|*int*|Seconds before the Magic Attach process expires|

### Raised exceptions

- `ConnectivityError`: Raised if it is not possible to connect to the Contracts
  Server.
- `ContractAPIError`: Raised if there is an unexpected error in the Contracts
  Server interaction.
- `MagicAttachUnavailable`: Raised if the Magic Attach service is busy or
  unavailable at the moment.

### CLI interaction

#### Calling from the CLI:

```bash
pro api u.pro.attach.magic.initiate.v1
```

#### Expected attributes in JSON structure

```json
{
    "user_code":"<UI_code>",
    "token":"<magic_token>",
    "expires": "<yyyy-MM-dd>T<HH:mm:ss>.<TZ>",
    "expires_in": 600
}
```

## u.pro.attach.magic.wait.v1

Introduced in Ubuntu Pro Client Version: `27.11~`

Polls the contract server waiting for the user to confirm the Magic Attach.

### Args

- `magic_token`: The Token provided by the initiate endpoint.

### Python API interaction

#### Calling from Python code

```python
from uaclient.api.u.pro.attach.magic.wait.v1 import MagicAttachWaitOptions, wait

options = MagicAttachWaitOptions(magic_token="<magic_token>")
result = wait(options)
```

#### Expected return object:

`uaclient.api.u.pro.attach.magic.wait.v1.MagicAttachWaitResult`

|Field Name|Type|Description|
|-|-|-|
|`user_code`|*str*|Code the user will see in the UI when confirming the Magic Attach|
|`token`|*str*|Magic Token used by the tooling to continue the operation|
|`expires`|*str*|Timestamp of the Magic Attach process expiration|
|`expires_in`|*int*|Seconds before the Magic Attach process expires|
|`contract_id`|*str*|ID of the contract the machine will be attached to|
|`contract_token`|*str*|The contract Token to attach the machine|

### Raised exceptions

- `ConnectivityError`: Raised if it is not possible to connect to the Contracts
  Server.
- `ContractAPIError`: Raised if there is an unexpected error in the Contracts
  Server interaction.
- `MagicAttachTokenError`: Raised when an invalid/expired Token is sent.
- `MagicAttachUnavailable`: Raised if the Magic Attach service is busy or
  unavailable at the moment.

### CLI interaction

#### Calling from the CLI:

```bash
pro api u.pro.attach.magic.wait.v1 --args magic_token=<magic_token>
```

#### Expected attributes in JSON structure

```json
{
    "user_code":"<UI_code>",
    "token":"<magic_token>",
    "expires": "<yyyy-MM-dd>T<HH:mm:ss>.<TZ>",
    "expires_in": 500,
    "contract_id": "<Contract-ID>",
    "contract_token": "<attach_token>",
}
```

## u.pro.attach.magic.revoke.v1

Introduced in Ubuntu Pro Client Version: `27.11~`

Revokes a Magic Attach Token.

### Args

- `magic_token`: The Token provided by the initiate endpoint.

### Python API interaction

#### Calling from Python code

```python
from uaclient.api.u.pro.attach.magic.revoke.v1 import MagicAttachRevokeOptions, revoke

options = MagicAttachWaitOptions(magic_token="<magic_token>")
result = revoke(options)
```

#### Expected return object:

`uaclient.api.u.pro.attach.magic.wait.v1.MagicAttachRevokeResult`

No data present in the result.

### Raised exceptions

- `ConnectivityError`: Raised if it is not possible to connect to the Contracts
  Server.
- `ContractAPIError`: Raised if there is an unexpected error in the Contracts
  Server interaction.
- `MagicAttachTokenAlreadyActivated`: Raised when trying to revoke a Token
  which was already activated through the UI.
- `MagicAttachTokenError`: Raised when an invalid/expired Token is sent.
- `MagicAttachUnavailable`: Raised if the Magic Attach service is busy or
  unavailable at the moment.

### CLI interaction

#### Calling from the CLI:

```bash
pro api u.pro.attach.magic.revoke.v1 --args magic_token=<token>
```

#### Expected attributes in JSON structure

```json
{}
```

## u.pro.attach.auto.should_auto_attach.v1

Introduced in Ubuntu Pro Client Version: `27.11~`

Checks if a given system should run auto-attach on boot.

### Args

This endpoint takes no arguments.

### Python API interaction

#### Calling from Python code

```python
from uaclient.api.u.pro.attach.auto.should_auto_attach.v1 import should_auto_attach

result = should_auto_attach()
```

#### Expected return object:

`uaclient.api.u.pro.attach.auto.should_auto_attach.v1.ShouldAutoAttachResult`

|Field Name|Type|Description|
|-|-|-|
|`should_auto_attach`|*bool*|True if the system should run auto-attach on boot|

### Raised exceptions

No exceptions raised by this endpoint.

### CLI interaction

#### Calling from the CLI:

```bash
pro api u.pro.attach.auto.should_auto_attach.v1
```

#### Expected attributes in JSON structure

```json
{
    "should_auto_attach": false
}
```

## u.pro.attach.auto.full_auto_attach.v1

Introduced in Ubuntu Pro Client Version: `27.11~`

Runs the whole auto-attach process on the system.

### Args

- `enable`: Optional list of services to enable after auto-attaching.
- `enable_beta`: Optional list of beta services to enable after auto-attaching.

```{note}
If none of the lists are set, the services will be enabled based on the
contract definitions.
```

### Python API interaction

#### Calling from Python code

```python
from uaclient.api.u.pro.attach.auto.full_auto_attach.v1 import full_auto_attach, FullAutoAttachOptions

options = FullAutoAttachOptions(enable=["<service1>", "<service2>"], enable_beta=["<beta_service3>"])
result = full_auto_attach(options)
```

#### Expected return object:

`uaclient.api.u.pro.attach.auto.full_auto_attach.v1.FullAutoAttachResult`

No data present in the result.

### Raised exceptions

- `AlreadyAttachedError`: Raised if running on a machine which is already
  attached to a Pro subscription.
- `AutoAttachDisabledError`: Raised if `disable_auto_attach: true` in
  `uaclient.conf`.
- `ConnectivityError`: Raised if it is not possible to connect to the Contracts
  Server.
- `ContractAPIError`: Raised if there is an unexpected error in the Contracts
  Server interaction.
- `EntitlementsNotEnabledError`: Raised if the Client fails to enable any of
  the entitlements (whether present in any of the lists or listed in the
  contract).
- `LockHeldError`: Raised if another Client process is holding the lock on the
  machine.
- `NonAutoAttachImageError`: Raised if the cloud where the system is running
  does not support auto-attach.
- `UserFacingError`: Raised if:
  - The Client is unable to determine which cloud the system is running on. 
  - The image where the Client is running does not support auto-attach.

### CLI interaction

#### Calling from the CLI:

This endpoint currently has no CLI support. Only the Python-based version is
available.

## u.pro.attach.auto.configure_retry_service.v1

Introduced in Ubuntu Pro Client Version: `27.12~`

Configures options for the retry auto-attach functionality, and creates files
that will activate the retry auto-attach functionality if
`ubuntu-advantage.service` runs.

Note that this does not start `ubuntu-advantage.service`. This makes it useful
for calling during the boot process `Before: ubuntu-advantage.service` so that
when `ubuntu-advantage.service` starts, its `ConditionPathExists` check passes
and activates the retry auto-attach function.

If you call this function outside of the boot process and would like the retry
auto-attach functionality to actually start, you'll need to call something
like `systemctl start ubuntu-advantage.service`.

### Args

- `enable`: Optional list of services to enable after auto-attaching.
- `enable_beta`: Optional list of beta services to enable after auto-attaching.

```{note}
If none of the lists are set, the services will be enabled based on the
contract definitions.
```

### Python API interaction

#### Calling from Python code

```python
from uaclient.api.u.pro.attach.auto.configure_retry_service.v1 import configure_retry_service, ConfigureRetryServiceOptions

options = ConfigureRetryServiceOptions(enable=["<service1>", "<service2>"], enable_beta=["<beta_service3>"])
result = configure_retry_service(options)
```

#### Expected return object:

`uaclient.api.u.pro.attach.auto.configure_retry_service.v1.ConfigureRetryServiceResult`

No data present in the result.

### Raised exceptions

No exceptions raised by this endpoint.

### CLI interaction

#### Calling from the CLI:

This endpoint currently has no CLI support. Only the Python-based version is
available.

## u.pro.security.status.livepatch_cves.v1

Introduced in Ubuntu Pro Client Version: `27.12~`

Lists Livepatch patches for the currently-running kernel.

### Args

This endpoint takes no arguments.

### Python API interaction

#### Calling from Python code

```python
from uaclient.api.u.pro.security.status.livepatch_cves.v1 import livepatch_cves

result = livepatch_cves()
```

#### Expected return object:

`uaclient.api.u.pro.security.status.livepatch_cves.v1.LivepatchCVEsResult`

|Field Name|Type|Description|
|-|-|-|
|`fixed_cves`|*list(LivepatchCVEObject)*|List of Livepatch patches for the given system|

`uaclient.api.u.pro.security.status.livepatch_cves.v1.LivepatchCVEObject`
|Field Name|Type|Description|
|-|-|-|
|`name`|*str*|Name (ID) of the CVE|
|`patched`|*bool*|Livepatch has patched the CVE|

### Raised exceptions

No exceptions raised by this endpoint.

### CLI interaction

#### Calling from the CLI:

```bash
pro api u.pro.security.status.livepatch_cves.v1
```

#### Expected attributes in JSON structure

```json
{
    "fixed_cves":[
        {
            "name": "<CVE Name>",
            "patched": true
        },
        {
            "name": "<Other CVE Name>",
            "patched": false
        },
    ],
}
```

## u.pro.security.status.reboot_required.v1

Introduced in Ubuntu Pro Client Version: `27.12~`

Informs if the system should be rebooted or not. Possible outputs are:
- `yes`: The system should be rebooted.
- `no`: There is no need to reboot the system.
- `yes-kernel-livepatches-applied`: There are Livepatch patches applied to the
  current kernel, but a reboot is required for an update to take place. This
  reboot can wait until the next maintenance window.

### Args

This endpoint takes no arguments.

### Python API interaction

#### Calling from Python code

```python
from uaclient.api.u.pro.security.status.reboot_required.v1 import reboot_required

result = reboot_required()
```

#### Expected return object:

`uaclient.api.u.pro.security.status.reboot_required.v1.RebootRequiredResult`

|Field Name|Type|Description|
|-|-|-|
|`reboot_required`|*str*|One of the descriptive strings indicating if the system should be rebooted|

### Raised exceptions

No exceptions raised by this endpoint.

### CLI interaction

#### Calling from the CLI:

```bash
pro api u.pro.security.status.reboot_required.v1
```

#### Expected attributes in JSON structure

```json
{
    "reboot_required": "yes|no|yes-kernel-livepatches-applied"
}
```

## u.pro.packages.summary.v1

Introduced in Ubuntu Pro Client Version: `27.12~`

Shows a summary of installed packages in the system, categorized by origin.

### Args

This endpoint takes no arguments.

### Python API interaction

#### Calling from Python code

```python
from uaclient.api.u.pro.packages.summary.v1 import summary

result = summary()
```

#### Expected return object:

`uaclient.api.u.pro.packages.summary.v1.PackageSummaryResult`

|Field Name|Type|Description|
|-|-|-|
|`summary`|*PackageSummary*|Summary of all installed packages|

`uaclient.api.u.pro.packages.summary.v1.PackageSummary`
|Field Name|Type|Description|
|-|-|-|
|`num_installed_packages`|*int*|Total count of installed packages|
|`num_esm_apps_packages`|*int*|Count of packages installed from `esm-apps`|
|`num_esm_infra_packages`|*int*|Count of packages installed from `esm-infra`|
|`num_main_packages`|*int*|Count of packages installed from `main`|
|`num_multiverse_packages`|*int*|Count of packages installed from `multiverse`|
|`num_restricted_packages`|*int*|Count of packages installed from `restricted`|
|`num_third_party_packages`|*int*|Count of packages installed from third party sources|
|`num_universe_packages`|*int*|Count of packages installed from `universe`|
|`num_unknown_packages`|*int*|Count of packages installed from unknown sources|

### Raised exceptions

No exceptions raised by this endpoint.

### CLI interaction

#### Calling from the CLI:

```bash
pro api u.pro.packages.summary.v1
```

#### Expected attributes in JSON structure

```json
{
    "summary":{
        "num_installed_packages": 1,
        "num_esm_apps_packages": 2,
        "num_esm_infra_packages": 3,
        "num_main_packages": 4,
        "num_multiverse_packages": 5,
        "num_restricted_packages": 6,
        "num_third_party_packages": 7,
        "num_universe_packages": 8,
        "num_unknown_packages": 9,
    },
}
```

## u.pro.packages.updates.v1

Introduced in Ubuntu Pro Client Version: `27.12~`

Shows available updates for packages in a system, categorized by where they
can be obtained.

### Args

This endpoint takes no arguments.

### Python API interaction

#### Calling from Python code

```python
from uaclient.api.u.pro.packages.updates.v1 import updates

result = updates()
```

#### Expected return object:

`uaclient.api.u.pro.packages.updates.v1.PackageUpdatesResult`

|Field Name|Type|Description|
|-|-|-|
|`summary`|*UpdateSummary*|Summary of all available updates|
|`updates`|*list(UpdateInfo)*|Detailed list of all available updates|

`uaclient.api.u.pro.packages.updates.v1.UpdateSummary`

|Field Name|Type|Description|
|-|-|-|
|`num_updates`|*int*|Total count of available updates|
|`num_esm_apps_updates`|*int*|Count of available updates from `esm-apps`|
|`num_esm_infra_updates`|*int*|Count of available updates from `esm-infra`|
|`num_standard_security_updates`|*int*|Count of available updates from the `-security` pocket|
|`num_standard_updates`|*int*|Count of available updates from the `-updates` pocket|

`uaclient.api.u.pro.packages.updates.v1.UpdateInfo`
|Field Name|Type|Description|
|-|-|-|
|`download_size`|*int*|Download size for the update in bytes|
|`origin`|*str*|Where the update is downloaded from|
|`package`|*str*|Name of the package to be updated|
|`provided_by`|*str*|Service which provides the update|
|`status`|*str*|Whether this update is ready for download or not|
|`version`|*str*|Version of the update|

### Raised exceptions

No exceptions raised by this endpoint.

### CLI interaction

#### Calling from the CLI:

```bash
pro api u.pro.packages.updates.v1
```

#### Expected attributes in JSON structure

```json
{
    "summary":{
        "num_updates": 1,
        "num_esm_apps_updates": 2,
        "num_esm_infra_updates": 3,
        "num_standard_security_updates": 4,
        "num_standard_updates": 5,
    },
    "updates":[
        {
            "download_size": 6,
            "origin": "<some site>",
            "package": "<package name>",
            "provided_by": "<service name>",
            "status": "<update status>",
            "version": "<updated version>",
        },
    ]
}
```

## u.pro.status.is_attached.v1

Introduced in Ubuntu Pro Client Version: `28~`

Shows if the machine is attached to a Pro subscription.

### Args

This endpoint takes no arguments.

### Python API interaction

#### Calling from Python code

```python
from uaclient.api.u.pro.status.is_attached.v1 import is_attached

result = is_attached()
```

#### Expected return object:

`uaclient.api.u.pro.status.is_attached.v1.IsAttachedResult`

|Field Name|Type|Description|
|-|-|-|
|`is_attached`|*bool*|If the machine is attached to a Pro subscription|

### CLI interaction

#### Calling from the CLI:

```bash
pro api u.pro.status.is_attached.v1
```

## u.pro.status.enabled_services.v1

Introduced in Ubuntu Pro Client Version: `28~`

Shows the Pro services that are enabled in the machine.

### Args

This endpoint takes no arguments.

### Python API interaction

#### Calling from Python code

```python
from uaclient.api.u.pro.status.enabled_services.v1 import enabled_services

result = enabled_services()
```

#### Expected return object:

`uaclient.api.u.pro.status.enabled_services.v1.EnabledServicesResult`

|Field Name|Type|Description|
|-|-|-|
|`enabled_services`|*List[EnabledService]*|A list of EnabledServices objects|

`uaclient.api.u.pro.status.enabled_services.v1.EnabledService`

|Field Name|Type|Description|
|-|-|-|
|`name`           |*str*           |name of the service                         |
|`variant_enabled`|*bool*          |If a variant of the service is enabled      |
|`variant_name`   |*Optional[str]* |name of the variant, if a variant is enabled|

### CLI interaction

#### Calling from the CLI:

```bash
pro api u.pro.status.enabled_services.v1
```

## u.security.package_manifest.v1

Introduced in Ubuntu Pro Client Version: `27.12~`

Returns the status of installed packages (`apt` and `snap`), formatted as a
manifest file (i.e. `package_name\tversion`).

### Args

This endpoint takes no arguments.

### Python API interaction

#### Calling from Python code

```python
from uaclient.api.u.security.package_manifest.v1 import package_manifest

result = package_manifest()
```

#### Expected return object:

`uaclient.api.u.security.package_manifest.v1.PackageManifestResult`

|Field Name|Type|Description|
|-|-|-|
|`manifest_data`|*str*|Manifest of `apt` and `snap` packages installed on the system|

### Raised exceptions

No exceptions raised by this endpoint.

### CLI interaction

#### Calling from the CLI:

```bash
pro api u.security.package_manifest.v1
```

#### Expected attributes in JSON structure

```json
{
    "package_manifest":"package1\t1.0\npackage2\t2.3\n"
}
```

## u.unattended_upgrades.status.v1

Introduced in Ubuntu Pro Client Version: `27.14~`

Returns the status around unattended-upgrades. The focus of the endpoint
is to verify if the application is running and how it is configured on
the machine.

```{important}
For this endpoint, we deliver a unique key under `meta` called `raw_config`. This field contains
all related unattended-upgrades configurations unparsed. This means that this field will maintain
both original name and values for those configurations.
``` 

### Args

This endpoint takes no arguments.

### Python API interaction

#### Calling from Python code

```python
from uaclient.api.u.unattended_upgrades.status.v1 import status

result = status()
```

#### Expected return object:
`uaclient.api.u.unattended_upgrades.status.v1.UnattendedUpgradesStatusResult

|Field Name|Type|Description|
|-|-|-|
|`systemd_apt_timer_enabled`|*bool*|Indicate if the apt-daily.timer jobs are enabled|
|`apt_periodic_job_enabled`|*bool*|Indicate if the APT::Periodic::Enabled configuration is turned off|
|`package_lists_refresh_frequency_days`|*int*|The value of the APT::Periodic::Update-Package-Lists configuration|
|`unattended_upgrades_frequency_days`|*int*|The value of the APT::Periodic::Unattended-Upgrade configuration|
|`unattended_upgrades_allowed_origins`|*List[str]*|The value of the Unattended-Upgrade::Allowed-Origins configuration|
|`unattended_upgrades_running`|*bool*|Indicate if the unattended-upgrade service is correctly configured and running|
|`unattended_upgrades_disabled_reason`|*object*|Object that explains why unattended-upgrades is not running. In case the application is running, the object will be null|
|`unatteded_upgrades_last_run`|`datetime.datetime`|The last time unattended-upgrades has run|

`uaclient.api.u.unattended_upgrades.status.v1.UnattendedUpgradesStatusDisabledReason`

|Field Name|Type|Description|
|-|-|-|
|`msg`|*str*|The reason why unattended-upgrades is not running in the system|
|`code`|*str*|The message code associated with the message|

### Raised exceptions

- `UnattendedUpgradesError`: Raised in case we cannot run a necessary command to show the status
  of unattended-upgrades

### CLI interaction

#### Calling from the CLI:

```bash
pro api u.unattended_upgrades.status.v1
```

#### Expected attributes in JSON structure

```json
{
    "apt_periodic_job_enabled": true,
    "package_lists_refresh_frequency_days": 1,
    "systemd_apt_timer_enabled": true,
    "unattended_upgrades_allowed_origins": [
      "${distro_id}:${distro_codename}",
      "${distro_id}:${distro_codename}-security",
      "${distro_id}ESMApps:${distro_codename}-apps-security",
      "${distro_id}ESM:${distro_codename}-infra-security"
    ],
    "unattended_upgrades_disabled_reason": null,
    "unattended_upgrades_frequency_days": 1,
    "unattended_upgrades_last_run": null,
    "unattended_upgrades_running": true
}
```

#### Possible attributes in JSON meta field
```json
{
    "meta": {
      "environment_vars": [],
      "raw_config": {
        "APT::Periodic::Enable": "1",
        "APT::Periodic::Unattended-Upgrade": "1",
        "APT::Periodic::Update-Package-Lists": "1",
        "Unattended-Upgrade::Allowed-Origins": [
          "${distro_id}:${distro_codename}",
          "${distro_id}:${distro_codename}-security",
          "${distro_id}ESMApps:${distro_codename}-apps-security",
          "${distro_id}ESM:${distro_codename}-infra-security"
        ]
      }
    }
}
```
