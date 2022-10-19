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
