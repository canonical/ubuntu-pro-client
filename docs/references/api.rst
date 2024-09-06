.. _api:

The Ubuntu Pro API reference guide
**********************************

The Ubuntu Pro Client has a Python-based API to be consumed by users who want
to integrate the Client's functionality with their software.

The functions and objects are available through the ``uaclient.api`` module,
and all of the available endpoints return an object with specific data for the
calls.

Besides importing the Python code directly, consumers who are not writing
Python may use the command line interface (CLI) to call the same functionality,
using the ``pro api`` command. This command will always return a JSON with a
standard structure, as can be seen below:

.. code-block:: json

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

Version dependencies
====================

The package name of Ubuntu Pro Client is ``ubuntu-advantage-tools``.

The documentation for each endpoint below states the first version to include
that endpoint.

If you depend on these endpoints, we recommend using a standard dependency
version requirement to ensure that a sufficiently up-to-date version of the Pro
Client is installed before trying to use it.

.. important::

   The ``~`` at the end of the version is important to ensure that ``dpkg``
   version comparison works as expected.

For example, if your software is packaged as a deb, then you can add the
following to your ``Depends`` list in your ``control`` file to ensure the
installed version is at least ``27.11~``:

.. code-block::

   ubuntu-advantage-tools (>= 27.11~)

Runtime version detection
-------------------------

If you need to detect the current version at runtime, the most reliable way is
to query ``dpkg``.

.. code-block:: bash

   dpkg-query --showformat='${Version}' --show ubuntu-advantage-tools

If you need to compare versions at runtime, make sure you use the ``dpkg``
version comparison algorithm. For example, the following will exit 0 if the
currently installed version of Pro Client is at least ``27.11~``:

.. code-block:: bash

   dpkg --compare-versions "$(dpkg-query --showformat='${Version}' --show ubuntu-advantage-tools)" ge "27.11~"

Runtime feature detection
-------------------------

As an alternative to version detection, you can use feature detection. This is
easier to do when importing the API in python than it is when using the
``pro api`` subcommand.

In python, try to import the desired endpoint. If an ``ImportError`` is raised,
then the currently installed version of Ubuntu Pro Client doesn't support that
endpoint.

For example:

.. code-block:: python

   try:
       from uaclient.api.u.pro.version.v1 import version
       pro_client_api_supported = True
   except ImportError:
       pro_client_api_supported = False

You could do something similar by catching certain errors when using the
``pro api`` subcommand, but there are more cases that could indicate an old
version, and it generally isn't recommended.

*Errors* and *warnings* fields
------------------------------

When using the API through the CLI, we use two distinct fields to list issues
to the users; *errors* and *warnings*.

Both of these fields contain a list of JSON objects explaining unexpected
behaviour during the execution of a command. For example, the *errors* field
will be populated like this if we have a connectivity issue when running a
``pro api`` command:

.. code-block:: json

   [
       {
           "title": "Failed to connect to authentication server",
           "code": "connectivity-error",
           "meta": {}
       }
   ]

*Warnings* follow the exact same structure as *errors*. The only difference is
that *warnings* means that the command was able to complete although unexpected
scenarios happened when executing the command.

CLI arguments
------------------------------

There are two ways to provide data to APIs that require arguments.

* ``--args``: Use this to individually provide arguments to the CLI endpoint.

  For example: ``pro api u.pro.attach.magic.revoke.v1 --args magic_token=TOKEN``

* ``--data``: Use this to provide a JSON object containing all the data:

  For example: ``pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-1234-1235"]}'``

.. include:: ./api_endpoints.txt
