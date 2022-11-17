# Pro API Reference Guide


The Pro Client has a Python-based API to be consumed by users who want to integrate the client's functionality to their software.
The functions and objects are available through the `uaclient.api` module, and all of the available endpoints return an object with specific data for the calls.

Besides importing the Python code directly, consumers who are not writing Python may use the CLI to call the same functionality, using the `pro api` command. This command will always return a JSON with a standard structure, as can be seen below:

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
- [u.security.package_manifest.v1](#usecuritypackage_manifestv1)

## u.pro.version.v1
Shows the installed Client version.

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
|installed_version|str|The current installed version|

### Raised Exceptions
- `VersionError`: raised if the client cannot determine the version


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
|user_code|str|Code the user will see in the UI when confirming the Magic Attach|
|token|str|Magic token used by the tooling to continue the operation|
|expires|str|Timestamp of the Magic Attach process expiration|
|expires_in|int|Seconds before the Magic Attach process expires|


### Raised Exceptions

- `ConnectivityError`: raised if it is not possible to connect to the Contracts Server
- `ContractAPIError`: raised if there is an unexpected error in the Contracts Server interaction
- `MagicAttachUnavailable`: raised if the Magic Attach service is busy or unavailable at the moment

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
Polls the contract server waiting for the user to confirm the Magic Attach.

### Args
- `magic_token`: The token provided by the initiate endpoint

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
|user_code|str|Code the user will see in the UI when confirming the Magic Attach|
|token|str|Magic token used by the tooling to continue the operation|
|expires|str|Timestamp of the Magic Attach process expiration|
|expires_in|int|Seconds before the Magic Attach process expires|
|contract_id|str|ID of the contract the machine will be attached to|
|contract_token|str|The contract token to attach the machine|


### Raised Exceptions

- `ConnectivityError`: raised if it is not possible to connect to the Contracts Server
- `ContractAPIError`: raised if there is an unexpected error in the Contracts Server interaction
- `MagicAttachTokenError`: raised when an invalid/expired token is sent
- `MagicAttachUnavailable`: raised if the Magic Attach service is busy or unavailable at the moment


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
Revokes a magic attach token.

### Args
- `magic_token`: The token provided by the initiate endpoint

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


### Raised Exceptions

- `ConnectivityError`: raised if it is not possible to connect to the Contracts Server
- `ContractAPIError`: raised if there is an unexpected error in the Contracts Server interaction
- `MagicAttachTokenAlreadyActivated`: raised when trying to revoke a token which was already activated through the UI
- `MagicAttachTokenError`: raised when an invalid/expired token is sent
- `MagicAttachUnavailable`: raised if the Magic Attach service is busy or unavailable at the moment


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
|should_auto_attach|bool|True if the system should run auto-attach on boot|

### Raised Exceptions
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
Runs the whole auto-attach process on the system.

### Args
- `enable`: optional list of services to enable after auto-attaching
- `enable_beta`: optional list of beta services to enable after auto-attaching

> If none of the lists are set, the services will be enabled based on the contract definitions.

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

### Raised Exceptions

- `AlreadyAttachedError`: raised if running on a machine which is already attached to a Pro subscription
- `AutoAttachDisabledError`: raised if `disable_auto_attach: true` in uaclient.conf
- `ConnectivityError`: raised if it is not possible to connect to the Contracts Server
- `ContractAPIError`: raised if there is an unexpected error in the Contracts Server interaction
- `EntitlementsNotEnabledError`: raised if the client fails to enable any of the entitlements
  (whether present in any of the lists or listed in the contract)
- `LockHeldError`: raised if another Client process is holding the lock on the machine
- `NonAutoAttachImageError`: raised if the cloud where the system is running does not support auto-attach
- `UserFacingError`: raised if:
  - the client is unable to determine on which cloud the system is running 
  - the image where the client is running does not support auto-attach


### CLI interaction
#### Calling from the CLI:
This endpoint currently has no CLI support. Only the Python-based version is available.


## u.pro.attach.auto.configure_retry_service.v1
Configures options for the retry auto attach functionality and create file that will activate the retry auto attach functionality if `ubuntu-advantage.service` runs.

Note that this does not start `ubuntu-advantage.service`. This makes it useful for calling during the boot process `Before: ubuntu-advantage.service` so that when `ubuntu-advantage.service` starts, its ConditionPathExists check passes and executes the retry auto attach function.

If you call this function outside of the boot process and would like the retry auto attach functionality to actually start, you'll need to call something like `systemctl start ubuntu-advantage.service`.


### Args
- `enable`: optional list of services to enable after auto-attaching
- `enable_beta`: optional list of beta services to enable after auto-attaching

> If none of the lists are set, the services will be enabled based on the contract definitions.

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

### Raised Exceptions
No exceptions raised by this endpoint.

### CLI interaction
#### Calling from the CLI:
This endpoint currently has no CLI support. Only the Python-based version is available.


## u.pro.security.status.livepatch_cves.v1
Lists Livepatch patches for the current running kernel.

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
|fixed_cves|list(LivepatchCVEObject)|List of Livepatch patches for the given system|

`uaclient.api.u.pro.security.status.livepatch_cves.v1.LivepatchCVEObject`
|Field Name|Type|Description|
|-|-|-|
|name|str|Name (ID) of the CVE|
|patched|bool|Livepatch has patched the CVE|


### Raised Exceptions
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
Informs if the system should be rebooted or not.
Possible outputs are:
- yes: the system should be rebooted
- no: there is no need to reboot the system
- yes-kernel-livepatches-applied: there are livepatch patches applied to the current kernel, but a reboot is required for an update to take place. This reboot can wait until the next maintenance window.

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
|reboot_required|str|One of the descriptive strings indicating if the system should be rebooted|

### Raised Exceptions
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
|summary|PackageSummary|Summary of all installed packages|

`uaclient.api.u.pro.packages.summary.v1.PackageSummary`
|Field Name|Type|Description|
|-|-|-|
|num_installed_packages|int|Total count of installed packages|
|num_esm_apps_packages|int|Count of packages installed from esm-apps|
|num_esm_infra_packages|int|Count of packages installed from esm-infra|
|num_main_packages|int|Count of packages installed from main|
|num_multiverse_packages|int|Count of packages installed from multiverse|
|num_restricted_packages|int|Count of packages installed from restricted|
|num_third_party_packages|int|Count of packages installed from third party sources|
|num_universe_packages|int|Count of packages installed from universe|
|num_unknown_packages|int|Count of packages installed from unknown sources|


### Raised Exceptions
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
Shows available updates for packages in a system, categorized by where they can be obtained.

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
|summary|UpdateSummary|Summary of all available updates|
|updates|list(UpdateInfo)|Detailed list of all available updates|

`uaclient.api.u.pro.packages.updates.v1.UpdateSummary`

|Field Name|Type|Description|
|-|-|-|
|num_updates|int|Total count of available updates|
|num_esm_apps_updates|int|Count of available updates from esm-apps|
|num_esm_infra_updates|int|Count of available updates from esm-infra|
|num_standard_security_updates|int|Count of available updates from the -security pocket|
|num_standard_updates|int|Count of available updates from the -updates pocket|

`uaclient.api.u.pro.packages.updates.v1.UpdateInfo`
|Field Name|Type|Description|
|-|-|-|
|download_size|int|Download size for the update in bytes|
|origin|str|Where the update is downloaded from|
|package|str|Name of the package to be updated|
|provided_by|str|Service which provides the update|
|status|str|Whether this update is ready for download or not|
|version|str|Version of the update|

### Raised Exceptions
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


## u.security.package_manifest.v1
Returns the status of installed packages (apt and snap), formatted as a
manifest file (i.e. `package_name\tversion`)

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
|manifest_data|str|Manifest of apt and snap packages installed on the system|

### Raised Exceptions
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
