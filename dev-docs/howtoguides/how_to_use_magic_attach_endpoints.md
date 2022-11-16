# How to use magic attach API endpoints

> **Note**
> Minimum version: 27.11

Th Ubuntu Pro Client provides three distinct endpoints to make it easier to perform
the magic attach flow. They are:

* u.pro.attach.magic.initiate.v1
* u.pro.attach.magic.wait.v1
* u.pro.attach.magic.revoke.v1

We will explain how to use each endpoint and what is the expected output for each of them.

## Initiate endpoint

To start the magic attach flow, we need to create a token for it. The initiate endpoint
will perform exactly that. When you run:

```console
$ pro api u.pro.attach.magic.initiate.v1
```

It is expected for you to see the following json response:

```json
{
  "_schema_version": "v1",
  "data": {
    "meta": {
       "environment_vars": []}
    },
    "attributes": {
      "expires": "EXPIRE_DATE",
      "expires_in": 10000,
      "token": "MAGIC_ATTACH_TOKEN",
      "user_code": "USER_CODE"
    },
    "type": "MagicAttachInitiate"
  },
  "errors": [],
  "result": "success",
  "version": "UBUNTU PRO CLIENT VERSION",
  "warnings": []
}
```

It is noteworthy here that the `attributes` contain both the `user_code` and `token`. The `user_code`
is the information that will be presented to the user, which it will make possible for the user
to validate the magic attach on the Ubuntu Pro portal. Additionally, the `token` information is required
for the other two API endpoints which will be described next.


## Wait endpoint

After we initiate the magic attach procedure, the user must go to the Ubuntu Pro portal and validate
the `user_code` it received. Once that is done, a contract token will be generated for the user, allowing
the attach procedure to begin. The wait endpoint will wait for the user to perform all of those
steps on the Ubuntu Pro portal. To call it, use:

```console
$ pro api u.pro.attach.magic.wait.v1 --args magic_token=MAGIC_ATTACH_TOKEN
```

Note here that the command requires the `token` that was generated in the initiate step. This command
will block and poll the server until there are any updates for that token. If the
user successfully performed the necessary steps on the Ubuntu Pro portal, we should see the following
response:

```json
{
  "_schema_version": "v1",
  "data": {
    "attributes": {
      "contract_id": "CONTRACT_ID",
      "contract_token": "CONTRACT_TOKEN",
      "expires": "EXPIRE_DATE",
      "expires_in": 10000,
      "token": "MAGIC_ATTACH_TOKEN",
      "user_code": "USER_CODE"
    }
    "type": "MagicAttachInitiate"
  },
  "errors": [],
  "result": "success",
  "version": "UBUNTU PRO CLIENT VERSION",
  "warnings": []
}
```

The `contract_token` is the token that can be used to perform an attach operation.

If the provided token is invalid or has expired, we will see the following response:

```json
{
  "_schema_version": "v1",
  "data": {
    "meta": {
      "environment_vars": []
    }
  },
  "errors": [
    {
      "code": "magic-attach-token-error",
      "meta": {},
      "title": "The magic attach token is invalid, has expired or never existed"
    }
  ],
  "result": "failure",
  "version": "UBUNTU PRO CLIENT VERSION",
  "warnings": []
}
```

It is expected that the token will be valid for about 10 minutes. Therefore, we expect the wait
command to keep polling for about that amount of time.


## Revoke

If we want to revoke the token created during the initiate call, we can use the revoke command:

```console
$ pro api u.pro.attach.magic.revoke.v1 --args magic_token=MAGIC_ATTACH_TOKEN
```

If the token is valid, we should see the following output:

```json
{
  "_schema_version": "v1",
  "data": {
    "attributes": {},
    "meta": {
      "environment_vars": []
    },
    "type": "MagicAttachRevoke"
  },
  "errors": [],
  "result": "success",
  "version": "PRO CLIENT VERSION",
  "warnings": []
}
```

However, if the token is already expired or even invalid, we will see the following output:

```json
{
  "_schema_version": "v1",
  "data": {
    "meta": {
      "environment_vars": []
    }
  },
  "errors": [
    {
      "code": "magic-attach-token-error",
      "meta": {},
      "title": "The magic attach token is invalid, has expired or never existed"
    }
  ],
  "result": "failure",
  "version": "PRO CLIENT VERSION",
  "warnings": []
}
```
