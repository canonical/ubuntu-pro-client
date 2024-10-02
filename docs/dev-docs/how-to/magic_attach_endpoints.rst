.. _magic_attach_endpoints:

How to use magic attach API endpoints
*************************************

.. note:: 
   Minimum Pro Client version: 27.11

The Ubuntu Pro Client provides three distinct endpoints to make it easier to
perform the "magic attach" flow. They are:

* ``u.pro.attach.magic.initiate.v1``
* ``u.pro.attach.magic.wait.v1``
* ``u.pro.attach.magic.revoke.v1``

We will explain how to use each endpoint and what the expected output for each
of them is.

Initiate endpoint
=================

To start the "magic attach" flow, we need to create a token for it. The
``initiate`` endpoint will do that. When you run:

.. code-block:: bash

   pro api u.pro.attach.magic.initiate.v1

You should see the following JSON response:

.. code-block:: json

    {
      "_schema_version": "v1",
      "data": {
        "meta": {
           "environment_vars": []
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

It is noteworthy here that the ``attributes`` contain both the ``user_code``
and ``token``.

* The ``user_code`` is presented to the user, so they can validate the magic
  attach on the Ubuntu Pro portal.
* The ``token`` information is required for the ``wait`` and ``revoke`` API
  endpoints.

Wait endpoint
=============

After we initiate the magic attach procedure, the user must go to the Ubuntu
Pro portal and validate the ``user_code`` they received. Then, a contract token
will be generated for the user, allowing the attach procedure to begin. The
``wait`` endpoint will wait for the user to perform these steps on the Ubuntu
Pro portal. To call it, use:

.. code-block:: bash

   pro api u.pro.attach.magic.wait.v1 --args magic_token=MAGIC_ATTACH_TOKEN

The command requires the ``token`` that was generated in the ``initiate`` step.
The ``wait`` command will block and poll the server until there are any updates
for that token. If the user successfully performed the necessary steps on the
Ubuntu Pro portal, we should see the following response:

.. code-block:: json

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

The ``contract_token`` is the token used to perform an ``attach`` operation.

If the provided token is invalid or has expired, we will see the following
response:

.. code-block:: json

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

The token will be valid for about 10 minutes. Therefore, we expect the ``wait``
command to continue polling for that amount of time.

Revoke endpoint
===============

If we want to revoke the token created during the ``initiate`` call, we can use
the ``revoke`` command:

.. code-block:: bash

   pro api u.pro.attach.magic.revoke.v1 --args magic_token=MAGIC_ATTACH_TOKEN

If the token is valid, we should see the following output:

.. code-block:: json

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

However, if the token has already expired or is invalid, we will see the
following output:

.. code-block:: json

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

