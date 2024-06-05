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
           "msg": "Failed to connect to authentication server",
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


Available endpoints
===================

The currently available endpoints are:

- `u.pro.version.v1`_
- `u.pro.attach.auto.configure_retry_service.v1`_
- `u.pro.attach.auto.full_auto_attach.v1`_
- `u.pro.attach.auto.should_auto_attach.v1`_
- `u.pro.attach.magic.initiate.v1`_
- `u.pro.attach.magic.revoke.v1`_
- `u.pro.attach.magic.wait.v1`_
- `u.pro.attach.token.full_token_attach.v1`_
- `u.pro.detach.v1`_
- `u.pro.packages.summary.v1`_
- `u.pro.packages.updates.v1`_
- `u.pro.security.fix.cve.execute.v1`_
- `u.pro.security.fix.cve.plan.v1`_
- `u.pro.security.fix.usn.execute.v1`_
- `u.pro.security.fix.usn.plan.v1`_
- `u.pro.security.status.livepatch_cves.v1`_
- `u.pro.security.status.reboot_required.v1`_
- `u.pro.services.dependencies.v1`_
- `u.pro.services.disable.v1`_
- `u.pro.services.enable.v1`_
- `u.pro.status.enabled_services.v1`_
- `u.pro.status.is_attached.v1`_
- `u.apt_news.current_news.v1`_
- `u.security.package_manifest.v1`_
- `u.unattended_upgrades.status.v1`_

u.pro.version.v1
================

This endpoint shows the installed Pro Client version.

- Introduced in Ubuntu Pro Client Version: ``27.11~``
- Args:

  - This endpoint takes no arguments.

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.pro.version.v1 import version

           result = version()

      - Expected return object:

        - ``uaclient.api.u.pro.version.v1.VersionResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``installed_version``
               - ``str``
               - The current installed version

      - Raised exceptions:

        - ``VersionError``: Raised if the Client cannot determine the version.

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.pro.version.v1

      - Expected attributes in JSON structure:

        .. code-block:: json

           {
              "installed_version":"<version>"
           }

u.pro.attach.auto.configure_retry_service.v1
============================================

This endpoint configures options for the retry auto-attach functionality, and
creates files that will activate the retry auto-attach functionality if
``ubuntu-advantage.service`` runs.

Note that this does not start ``ubuntu-advantage.service``. This makes it useful
for calling during the boot process ``Before: ubuntu-advantage.service`` so that
when ``ubuntu-advantage.service`` starts, its ``ConditionPathExists`` check
passes and activates the retry auto-attach function.

If you call this function outside of the boot process and would like the retry
auto-attach functionality to actually start, you'll need to call something
like ``systemctl start ubuntu-advantage.service``.

- Introduced in Ubuntu Pro Client Version: ``27.12~``
- Args:

  - ``enable``: Optional list of services to enable after auto-attaching.
  - ``enable_beta``: Optional list of beta services to enable after
    auto-attaching.

.. note::

   If none of the lists are set, the services will be enabled based on the
   contract definitions.

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.pro.attach.auto.configure_retry_service.v1 import configure_retry_service, ConfigureRetryServiceOptions

           options = ConfigureRetryServiceOptions(enable=["<service1>", "<service2>"], enable_beta=["<beta_service3>"])
           result = configure_retry_service(options)

      - Expected return object:

        - ``uaclient.api.u.pro.attach.auto.configure_retry_service.v1.ConfigureRetryServiceResult``

          No data present in the result.

      - Raised exceptions:

        - No exceptions raised by this endpoint.

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        - This endpoint currently has no CLI support. Only the Python-based
          version is available.

u.pro.attach.auto.full_auto_attach.v1
=====================================

This endpoint runs the whole auto-attach process on the system.

- Introduced in Ubuntu Pro Client Version: ``27.11~``
- Args:

  - ``enable``: Optional list of services to enable after auto-attaching.
  - ``enable_beta``: Optional list of beta services to enable after auto-attaching.

.. note::

   If none of the lists are set, the services will be enabled based on the
   contract definitions.

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.pro.attach.auto.full_auto_attach.v1 import full_auto_attach, FullAutoAttachOptions

           options = FullAutoAttachOptions(enable=["<service1>", "<service2>"], enable_beta=["<beta_service3>"])
           result = full_auto_attach(options)

      - Expected return object:

        - ``uaclient.api.u.pro.attach.auto.full_auto_attach.v1.FullAutoAttachResult``

          No data present in the result.

      - Raised exceptions

        - ``AlreadyAttachedError``: Raised if running on a machine which is
          already attached to a Pro subscription.
        - ``AutoAttachDisabledError``: Raised if ``disable_auto_attach: true``
          in ``uaclient.conf``.
        - ``ConnectivityError``: Raised if it is not possible to connect to the
          contracts service.
        - ``ContractAPIError``: Raised if there is an unexpected error in the
          contracts service interaction.
        - ``EntitlementsNotEnabledError``: Raised if the Client fails to enable
          any of the entitlements (whether present in any of the lists or
          listed in the contract).
        - ``LockHeldError``: Raised if another Client process is holding the
          lock on the machine.
        - ``NonAutoAttachImageError``: Raised if the cloud where the system is
          running does not support auto-attach.
        - ``UserFacingError``: Raised if:

          - The Client is unable to determine which cloud the system is running
            on. 
          - The image where the Client is running does not support auto-attach.

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        This endpoint currently has no CLI support. Only the Python-based
        version is available.

u.pro.attach.auto.should_auto_attach.v1
=======================================

This endpoint checks if a given system should run auto-attach on boot.

- Introduced in Ubuntu Pro Client Version: ``27.11~``
- Args:

  - This endpoint takes no arguments.

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.pro.attach.auto.should_auto_attach.v1 import should_auto_attach

           result = should_auto_attach()

      - Expected return object:

        - ``uaclient.api.u.pro.attach.auto.should_auto_attach.v1.ShouldAutoAttachResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``should_auto_attach``
               - ``bool``
               - True if the system should run auto-attach on boot

      - Raised exceptions:

        - No exceptions raised by this endpoint.

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.pro.attach.auto.should_auto_attach.v1

      - Expected attributes in JSON structure:

        .. code-block:: json

           {
               "should_auto_attach": false
           }

u.pro.attach.magic.initiate.v1
==============================

This endpoint initiates the Magic Attach flow, retrieving the User Code to
confirm the operation and the Token used to proceed.

- Introduced in Ubuntu Pro Client Version: ``27.11~``
- Args:

  - This endpoint takes no arguments.

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.pro.attach.magic.initiate.v1 import initiate

           result = initiate()

      - Expected return object:

        - ``uaclient.api.u.pro.attach.magic.initiate.v1.MagicAttachInitiateResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``user_code``
               - ``str``
               - Code the user will see in the UI when confirming the Magic Attach
             * - ``token``
               - ``str``
               - Magic Token that can be used in either `u.pro.attach.magic.revoke.v1`_ or `u.pro.attach.magic.wait.v1`_
             * - ``expires``
               - ``str``
               - Timestamp of the Magic Attach process expiration
             * - ``expires_in``
               - ``int``
               - Seconds before the Magic Attach process expires

      - Raised exceptions:

        - ``ConnectivityError``: Raised if it is not possible to connect to the
          contracts service.
        - ``ContractAPIError``: Raised if there is an unexpected error in the
          contracts service interaction.
        - ``MagicAttachUnavailable``: Raised if the Magic Attach service is
          busy or unavailable at the moment.

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.pro.attach.magic.initiate.v1

      - Expected attributes in JSON structure:

        .. code-block:: json

           {
              "user_code":"<UI_code>",
              "token":"<magic_token>",
              "expires": "<yyyy-MM-dd>T<HH:mm:ss>.<TZ>",
              "expires_in": 600
           }


u.pro.attach.magic.revoke.v1
============================

This endpoint revokes a Magic Attach Token.

- Introduced in Ubuntu Pro Client Version: ``27.11~``
- Args:

  - ``magic_token``: The Token provided by the initiate endpoint.

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.pro.attach.magic.revoke.v1 import MagicAttachRevokeOptions, revoke

           options = MagicAttachWaitOptions(magic_token="<magic_token>")
           result = revoke(options)

      - Expected return object:

        - ``uaclient.api.u.pro.attach.magic.wait.v1.MagicAttachRevokeResult``

          No data present in the result.

      - Raised exceptions:

        - ``ConnectivityError``: Raised if it is not possible to connect to the
          contracts service.
        - ``ContractAPIError``: Raised if there is an unexpected error in the
          contracts service interaction.
        - ``MagicAttachTokenAlreadyActivated``: Raised when trying to revoke a
          Token which was already activated through the UI.
        - ``MagicAttachTokenError``: Raised when an invalid/expired Token is
          sent.
        - ``MagicAttachUnavailable``: Raised if the Magic Attach service is busy
          or unavailable at the moment.

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.pro.attach.magic.revoke.v1 --args magic_token=<token>

      - Expected attributes in JSON structure:

        .. code-block:: json

           {}

u.pro.attach.magic.wait.v1
==========================

This endpoint polls the contracts service waiting for the user to confirm the
Magic Attach.

- Introduced in Ubuntu Pro Client Version: ``27.11~``
- Args:

  - ``magic_token``: The Token provided by the initiate endpoint.

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.pro.attach.magic.wait.v1 import MagicAttachWaitOptions, wait

           options = MagicAttachWaitOptions(magic_token="<magic_token>")
           result = wait(options)

      - Expected return object:

        - ``uaclient.api.u.pro.attach.magic.wait.v1.MagicAttachWaitResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``user_code``
               - ``str``
               - Code the user will see in the UI when confirming the Magic Attach
             * - ``token``
               - ``str``
               - The same Magic Token that was sent as an argument
             * - ``expires``
               - ``str``
               - Timestamp of the Magic Attach process expiration
             * - ``expires_in``
               - ``int``
               - Seconds before the Magic Attach process expires
             * - ``contract_id``
               - ``str``
               - ID of the contract the machine will be attached to
             * - ``contract_token``
               - ``str``
               - The contract Token to attach the machine

      - Raised exceptions:

        - ``ConnectivityError``: Raised if it is not possible to connect to the
          contracts service.
        - ``ContractAPIError``: Raised if there is an unexpected error in the
          contracts service interaction.
        - ``MagicAttachTokenError``: Raised when an invalid/expired Token is
          sent.
        - ``MagicAttachUnavailable``: Raised if the Magic Attach service is
          busy or unavailable at the moment.

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.pro.attach.magic.wait.v1 --args magic_token=<magic_token>

      - Expected attributes in JSON structure:

        .. code-block:: json

           {
               "user_code":"<UI_code>",
               "token":"<magic_token>",
               "expires": "<yyyy-MM-dd>T<HH:mm:ss>.<TZ>",
               "expires_in": 500,
               "contract_id": "<Contract-ID>",
               "contract_token": "<attach_token>",
           }

u.pro.attach.token.full_token_attach.v1
============================================

This endpoint allow the user to attach to a Pro subscription using
a token.

- Introduced in Ubuntu Pro Client Version: ``32~``
- Args:

  - ``token``: The token associated with a Pro subscription
  - ``auto_enable_services``: If false, the attach operation will not enable any service during the
    operation

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.pro.attach.token.full_token_attach.v1 import full_token_attach, FullTokenAttachOptions

           options = FullTokenAttachOptions(token="TOKEN")
           result = full_token_attach(options)

      - Expected return object:

        - ``uaclient.api.u.pro.attach.token.full_token_attach.v1.FullTokenAttachResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``enabled``
               - ``List[str]``
               - The services enabled during the attach operation
             * - ``reboot_required``
               - ``bool``
               - True if the system requires a reboot after the attach operation

      - Raised exceptions:

        - ``NonRootUserError``: Raised if a non-root user executes this endpoint

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.pro.attach.token.full_token_attach.v1

        Note that we don't need to explicitly pass the token when calling the CLI command.
        If we define a JSON file (i.e. ``file.json``) with the same attributes as the options for this endpoint:

        .. code-block:: json

           {
               "token": "TOKEN",
               "auto_enable_services": false
           }

        Then we can call the API like this:

        .. code-block:: bash

           cat file.json | pro api u.pro.attach.token.full_token_attach.v1 --data -

      - Expected attributes in JSON structure:

        .. code-block:: json

           {
               "enabled": ["service1", "service2"],
               "reboot_required": false
           }

u.pro.detach.v1
============================================

This endpoint allow the user to detach the machine from a Pro subscription.

- Introduced in Ubuntu Pro Client Version: ``32~``

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.pro.detach.v1 import detach

           result = detach()

      - Expected return object:

        - ``uaclient.api.u.pro.detach.v1.DetachResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``disabled``
               - ``List[str]``
               - The services disabled during the detach operation
             * - ``reboot_required``
               - ``bool``
               - True if the system requires a reboot after the detach operation

      - Raised exceptions:

        - ``NonRootUserError``: Raised if a non-root user executes this endpoint

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.pro.detach.v1

      - Expected attributes in JSON structure:

        .. code-block:: json

           {
               "disabled": ["service1", "service2"],
               "reboot_required": false
           }

u.pro.packages.summary.v1
=========================

This endpoint shows a summary of installed packages in the system, categorised
by origin.

- Introduced in Ubuntu Pro Client Version: ``27.12~``
- Args:

  - This endpoint takes no arguments.

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.pro.packages.summary.v1 import summary

           result = summary()

      - Expected return object:

        - ``uaclient.api.u.pro.packages.summary.v1.PackageSummaryResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``summary``
               - ``PackageSummary``
               - Summary of all installed packages

        - ``uaclient.api.u.pro.packages.summary.v1.PackageSummary``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``num_installed_packages``
               - ``int``
               - Total count of installed packages
             * - ``num_esm_apps_packages``
               - ``int``
               - Count of packages installed from ``esm-apps``
             * - ``num_esm_infra_packages``
               - ``int``
               - Count of packages installed from ``esm-infra``
             * - ``num_main_packages``
               - ``int``
               - Count of packages installed from ``main``
             * - ``num_multiverse_packages``
               - ``int``
               - Count of packages installed from ``multiverse``
             * - ``num_restricted_packages``
               - ``int``
               - Count of packages installed from ``restricted``
             * - ``num_third_party_packages``
               - ``int``
               - Count of packages installed from third party sources
             * - ``num_universe_packages``
               - ``int``
               - Count of packages installed from ``universe``
             * - ``num_unknown_packages``
               - ``int``
               - Count of packages installed from unknown sources

      - Raised exceptions:

        - No exceptions raised by this endpoint.

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.pro.packages.summary.v1

      - Expected attributes in JSON structure:

        .. code-block:: json

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

u.pro.packages.updates.v1
=========================

This endpoint shows available updates for packages in a system, categorised by
where they can be obtained.

- Introduced in Ubuntu Pro Client Version: ``27.12~``
- Args:

  - This endpoint takes no arguments.

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.pro.packages.updates.v1 import updates

           result = updates()

      - Expected return object:

        - ``uaclient.api.u.pro.packages.updates.v1.PackageUpdatesResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``summary``
               - ``UpdateSummary``
               - Summary of all available updates
             * - ``updates``
               - ``List[UpdateInfo]``
               - Detailed list of all available updates

        - ``uaclient.api.u.pro.packages.updates.v1.UpdateSummary``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``num_updates``
               - ``int``
               - Total count of available updates
             * - ``num_esm_apps_updates``
               - ``int``
               - Count of available updates from ``esm-apps``
             * - ``num_esm_infra_updates``
               - ``int``
               - Count of available updates from ``esm-infra``
             * - ``num_standard_security_updates``
               - ``int``
               - Count of available updates from the ``-security`` pocket
             * - ``num_standard_updates``
               - ``int``
               - Count of available updates from the ``-updates`` pocket

        - ``uaclient.api.u.pro.packages.updates.v1.UpdateInfo``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``download_size``
               - ``int``
               - Download size for the update in bytes
             * - ``origin``
               - ``str``
               - Where the update is downloaded from
             * - ``package``
               - ``str``
               - Name of the package to be updated
             * - ``provided_by``
               - ``str``
               - Service which provides the update
             * - ``status``
               - ``str``
               - Whether this update is ready for download or not
             * - ``version``
               - ``str``
               - Version of the update

      - Raised exceptions:

        - No exceptions raised by this endpoint.   

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.pro.packages.updates.v1

      - Expected attributes in JSON structure:

        .. code-block:: json

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

.. _cve-execute-api-v1:

u.pro.security.fix.cve.execute.v1
===================================

This endpoint fixes the specified CVEs on the machine.

- Introduced in Ubuntu Pro Client Version: ``30~``
- Args:

  - ``cves``: A list of CVE (i.e. CVE-2023-2650) titles

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.pro.security.fix.cve.execute.v1 import execute, CVEFixExecuteOptions

           options = CVEFixExecuteOptions(cves=["CVE-1234-1234", "CVE-1234-1235"])
           result = execute(options)

      - Expected return object:

        - ``uaclient.api.u.pro.security.fix.cve.execute.v1.CVESAPIFixExecuteResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``cves_data``
               - ``List[CVEAPIFixExecuteResult]``
               - A list of CVEAPIFixExecuteResult objects

        - ``uaclient.api.u.pro.security.fix.cve.execute.v1.CVEAPIFixExecuteResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``status``
               - ``str``
               - The status of fixing the CVEs
             * - ``cves``
               - ``List[FixExecuteResult]``
               - A list of FixExecuteResult objects

        - ``uaclient.api.u.pro.security.fix._common.execute.v1.FixExecuteResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``title``
               - ``str``
               - The title of the CVE
             * - ``expected_status``
               - ``str``
               - The status of fixing the CVE
             * - ``upgraded_packages``
               - ``List[UpgradedPackage]``
               - A list of UpgradedPackage objects
             * - ``error``
               - ``Optional[FixExecuteError]``
               - A FixExecuteError object

        - ``uaclient.api.u.pro.security.fix._common.execute.v1.UpgradedPackage``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``name``
               - ``str``
               - The name of the package
             * - ``version``
               - ``str``
               - The version that the package was upgraded to
             * - ``pocket``
               - ``str``
               - The pocket which contained the package upgrade

        - ``uaclient.api.u.pro.security.fix._common.execute.v1.FixExecuteError``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``error_type``
               - ``str``
               - The type of the error
             * - ``reason``
               - ``str``
               - The reason why the error occurred
             * - ``failed_upgrades``
               - ``Optional[List[FailedUpgrade]]``
               - A list of FailedUpgrade objects

        - ``uaclient.api.u.pro.security.fix._common.execute.v1.FailedUpgrade``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``name``
               - ``str``
               - The name of the package
             * - ``pocket``
               - ``str``
               - The pocket which contained the package upgrade

      - Raised exceptions:

        - No exceptions raised by this endpoint.   

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.pro.security.fix.cve.execute.v1 --data '{"cves": ["CVE-1234-1234", "CVE-1234-1235"]}'

      - Expected attributes in JSON structure:

        .. code-block:: json

           {
              "cves_data": {
                  "status": "fixed",
                  "cves": [
                    {
                        "title": "CVE-1234-56789",
                        "status": "fixed",
                        "upgraded_packages": {
                            "name": "pkg1",
                            "version": "1.1",
                            "pocket": "standard-updates"
                        },
                        "error": null
                    }
                  ]
              }
           }

   .. tab-item:: Explanation
      :sync: explanation

      When using the CVE endpoint, the expected output is as follows:

      .. code-block:: json

         {
           "_schema_version": "v1",
           "data": {
             "attributes": {
               "cves_data": {
                 "cves": [
                   {
                     "description": "description",
                     "errors": null,
                     "status": "fixed",
                     "title": "CVE-2021-27135",
                     "upgraded_packages": [
                       {
                         "name": "xterm",
                         "pocket": "standard-updates",
                         "version": "VERSION"
                       }
                     ]
                   }
                 ],
                 "status": "fixed"
               }
             },
             "meta": {
               "environment_vars": []
             },
             "type": "CVEFixExecute"
           },
           "errors": [],
           "result": "success",
           "version": "30",
           "warnings": []
         }

      From this output, we can see that the **cves_data** object contains two attributes:

      * **cves**: A list of CVE objects detailing what happened during the fix operation.
      * **status**: The status of the fix operation considering **all** CVEs.
                    This means that if one CVE cannot be fixed, this field will reflect that.

      If we take a look at a CVE object, we will see the following structure:

      * **title**: The title of the CVE.
      * **description**: The CVE description.
      * **error**: Any error captured when fixing the CVE will appear here. The error object
                  will be detailed in a following section.
      * **status**: The expected status of the CVE after the fix operation. There are
        three possible scenarios: **fixed**, **still-affected** and **not-affected**.
        The system is considered **still-affected** if there is something that
        prevents any required packages from being upgraded. The system
        is considered **not-affected** if the CVE doesn't affect the system at all.
      * **upgraded_packages**: A list of UpgradedPackage objects referencing each package
        that was upgraded during the fix operation. The UpgradedPackage object always contain
        the **name** of the package, the **version** it was upgraded to and the **pocket** where
        the package upgrade came from.

      **What errors can be generated?**

      There some errors that can happen when executing this endpoint. For example, the system
      might require the user to attach to a Pro subscription to install the upgrades,
      or the user might run the command as non-root when a package upgrade is needed.

      In those situations, the error JSON error object will follow this representation:

      .. code-block:: json

         {
           "error_type": "error-type",
           "reason": "reason",
           "failed_upgrades": [
             {
               "name": "pkg1",
               "pocket": "esm-infra"
             }
           ]
         }

      We can see that the representation has the following fields:

      * **error_type**: The error type
      * **reason**: The explanation of why the error happened
      * **failed_upgrade**: A list of objects that always contain the name of the package
        that was not upgraded and the pocket where the upgrade would have come from.

u.pro.security.fix.cve.plan.v1
===============================

This endpoint shows the necessary steps required to fix CVEs in the system without
executing any of those steps.

- Introduced in Ubuntu Pro Client Version: ``29~``
- Args:

  - ``cves``: A list of CVE (i.e. CVE-2023-2650) titles

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.pro.security.fix.cve.plan.v1 import plan, CVEFixPlanOptions

           options = CVEFixPlanOptions(cves=["CVE-1234-1234", "CVE-1234-1235"])
           result = plan(options)

      - Expected return object:

        - ``uaclient.api.u.pro.security.fix.cve.plan.v1.CVESFixPlanResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``cves_data``
               - ``List[CVEFixPlanResult]``
               - A list of ``CVEFixPlanResult`` objects

        - ``uaclient.api.u.pro.security.fix.cve.plan.v1.CVEFixPlanResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``expected_status``
               - ``str``
               - The expected status of fixing the CVEs
             * - ``cves``
               - ``List[FixPlanResult]``
               - A list of ``FixPlanResult`` objects

        - ``uaclient.api.u.pro.security.fix.FixPlanResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``title``
               - ``str``
               - The title of the CVE
             * - ``expected_status``
               - ``str``
               - The expected status of fixing the CVE
             * - ``plan``
               - ``List[FixPlanStep]``
               - A list of FixPlanStep objects
             * - ``warnings``
               - ``List[FixPlanWarning]``
               - A list of FixPlanWarning objects
             * - ``error``
               - ``Optional[FixPlanError]``
               - A list of FixPlanError objects
             * - ``additional_data``
               - ``AdditionalData``
               - Additional data for the CVE

        - ``uaclient.api.u.pro.security.fix.FixPlanStep``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``operation``
               - ``str``
               - The operation that would be performed to fix the CVE. This can be either an attach, enable, apt-upgrade or a no-op type
             * - ``order``
               - ``int``
               - The execution order of the operation
             * - ``data``
               - ``object``
               - A data object that can be either an ``AptUpgradeData``, ``AttachData``, ``EnableData``, ``NoOpData``

        - ``uaclient.api.u.pro.security.fix.FixPlanWarning``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``warning_type``
               - ``str``
               - The type of warning
             * - ``order``
               - ``int``
               - The execution order of the operation
             * - ``data``
               - ``object``
               - A data object that represents either an PackageCannotBeInstalledData or a SecurityIssueNotFixedData

        - ``uaclient.api.u.pro.security.fix.FixPlanError``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``msg``
               - ``str``
               - The error message
             * - ``code``
               - ``str``
               - The message code

        - ``uaclient.api.u.pro.security.fix.AdditionalData``

            For a CVE, we don't expect any additional data at the moment

        - ``uaclient.api.u.pro.security.fix.AptUpgradeData``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``binary_packages``
               - ``List[str]``
               - A list of binary packages that need to be upgraded
             * - ``source_packages``
               - ``List[str]``
               - A list of source packages that need to be upgraded
             * - ``pocket``
               - ``str``
               - The pocket where the packages will be installed from

        - ``uaclient.api.u.pro.security.fix.AttachData``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``reason``
               - ``str``
               - The reason why an attach operation is needed
             * - ``source_packages``
               - ``List[str]``
               - The source packages that require the attach operation
             * - ``required_service``
               - ``str``
               - The required service that requires the attach operation

        - ``uaclient.api.u.pro.security.fix.EnableData``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``service``
               - ``str``
               - The Pro client service that needs to be enabled
             * - ``source_packages``
               - ``str``
               - The source packages that require the service to be enabled

        - ``uaclient.api.u.pro.security.fix.NoOpData``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``status``
               - ``str``
               - The status of the CVE when no operation can be performed

        - ``uaclient.api.u.pro.security.fix.NoOpAlreadyFixedData``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``status``
               - ``str``
               - The status of the CVE when no operation can be performed
             * - ``source_packages``
               - ``str``
               - The source packages that are already fixed
             * - ``pocket``
               - ``str``
               - The pocket where the packages would have been installed from

        - ``uaclient.api.u.pro.security.fix.NoOpLivepatchFixData``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``status``
               - ``str``
               - The status of the CVE when no operation can be performed
             * - ``patch_version``
               - ``str``
               - Version of the path from Livepatch that fixed the CVE

        - ``uaclient.api.u.pro.security.fix.PackageCannotBeInstalledData``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``binary_package``
               - ``str``
               - The binary package that cannot be installed
             * - ``binary_package_version``
               - ``str``
               - The version of the binary package that cannot be installed
             * - ``source_package``
               - ``str``
               - The source package associated with the binary package
             * - ``related_source_packages``
               - ``List[str]``
               - A list of source packages that comes from the same pocket as the affected package
             * - ``pocket``
               - ``str``
               - The pocket where the affected package should be installed from

        - ``uaclient.api.u.pro.security.fix.SecurityIssueNotFixedData``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``source_packages``
               - ``List[str]``
               - A list of source packages that cannot be fixed at the moment
             * - ``status``
               - ``str``
               - The status of the CVE regarding those packages

      - Raised exceptions:

        - No exceptions raised by this endpoint.   

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-1234-56789", "CVE-1234-1235"]}'

      - Expected attributes in JSON structure:

        .. code-block:: json

           {
              "cves_data": {
                  "expected_status": "fixed",
                  "cves": [
                    {
                        "title": "CVE-1234-56789",
                        "expected_status": "fixed",
                        "plan": [
                            {
                                "operation": "apt-upgrade",
                                "order": 1,
                                "data": {
                                    "binary_packages": ["pkg1"],
                                    "source_packages": ["pkg1"],
                                    "pocket": "standard-updates",
                                }
                            }
                        ],
                        "warnings": [],
                        "error": null,
                        "additional_data": {}
                    }
                  ]
              }
           }

u.pro.security.fix.usn.execute.v1
===================================

This endpoint fixes the specified USNs on the machine.

- Introduced in Ubuntu Pro Client Version: ``30~``
- Args:

  - ``usns``: A list of USNs (i.e. USN-6188-1) titles

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.pro.security.fix.usn.execute.v1 import execute, USNFixExecuteOptions

           options = USNFixExecuteOptions(usns=["USN-1234-1", "USN-1235-1"])
           result = execute(options)

      - Expected return object:

        - ``uaclient.api.u.pro.security.fix.usn.execute.v1.USNSAPIFixExecuteResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``usns_data``
               - ``List[USNAPIFixExecuteResult]``
               - A list of USNAPIFixExecuteResult objects

        - ``uaclient.api.u.pro.security.fix.usn.execute.v1.USNAPIFixExecuteResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``status``
               - ``str``
               - The status of fixing the USNs
             * - ``cves``
               - ``List[FixExecuteUSNResult]``
               - A list of FixExecuteResult objects

        - ``uaclient.api.u.pro.security.fix.usn.execute.v1.FixExecuteUSNResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``target_usn``
               - ``str``
               - The FixExecuteResult for the target USN
             * - ``related_usns``
               - ``List[FixExecuteResult]``
               - A list of FixExecuteResult objects for the related USNs

        - ``uaclient.api.u.pro.security.fix._common.execute.v1.FixExecuteResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``title``
               - ``str``
               - The title of the USN
             * - ``expected_status``
               - ``str``
               - The status of fixing the USN
             * - ``upgraded_packages``
               - ``List[UpgradedPackage]``
               - A list of UpgradedPackage objects
             * - ``error``
               - ``Optional[FixExecuteError]``
               - A FixExecuteError object

        - ``uaclient.api.u.pro.security.fix._common.execute.v1.UpgradedPackage``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``name``
               - ``str``
               - The name of the package
             * - ``version``
               - ``str``
               - The version that the package was upgraded to
             * - ``pocket``
               - ``str``
               - The pocket which contained the package upgrade

        - ``uaclient.api.u.pro.security.fix._common.execute.v1.FixExecuteError``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``error_type``
               - ``str``
               - The type of the error
             * - ``reason``
               - ``str``
               - The reason why the error occurred
             * - ``failed_upgrades``
               - ``Optional[List[FailedUpgrade]]``
               - A list of FailedUpgrade objects

        - ``uaclient.api.u.pro.security.fix._common.execute.v1.FailedUpgrade``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``name``
               - ``str``
               - The name of the package
             * - ``pocket``
               - ``str``
               - The pocket which contained the package upgrade

      - Raised exceptions:

        - No exceptions raised by this endpoint.   

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.pro.security.fix.usn.execute.v1 --data '{"usns": ["USN-1234-1", "USN-1235-1"]}'

      - Expected attributes in JSON structure:

        .. code-block:: json

           {
              "usns_data": {
                  "status": "fixed",
                  "usns": [
                    {
                        "target_usn": {
                            "title": "CVE-1234-56789",
                            "status": "fixed",
                            "upgraded_packages": {
                                "name": "pkg1",
                                "version": "1.1",
                                "pocket": "standard-updates"
                            },
                            "error": null
                        },
                        "related_usns": []
                    }
                  ]
              }
           }

   .. tab-item:: Explanation
      :sync: explanation

      When using the USN endpoint, the expected output is as follows:

      .. code-block:: json

          {
            "usns_data": {
                "status": "fixed",
                "usns": [
                  {
                      "target_usn": {
                          "title": "CVE-1234-56789",
                          "status": "fixed",
                          "upgraded_packages": {
                              "name": "pkg1",
                              "version": "1.1",
                              "pocket": "standard-updates"
                          },
                          "error": null
                      },
                      "related_usns": []
                  }
                ]
            }
          }

      From this output, we can see that the **usns_data** object contains two attributes:

      * **usns**: A list of USN objects detailing what happened during the fix operation.
      * **status**: The status of the fix operation considering **all** USNs.
                    This means that if one USN cannot be fixed, this field will reflect that.
                    Note that related USNs don't interfere with this attribute, meaning
                    that a related USN can fail to be fixed without modifying the **status**
                    value.

      Each **usn** object contains a reference for both **target_usn** and **related_usns**.
      The target is the USN requested to be fixed by the user, while related USNs are USNs
      that are related to the main USN and an attempt to fix them will be performed by the
      endpoint too. To better understand that distinction, please refer to 
      :ref:`our explanation of CVEs and USNs <expl-cve-usn>`.

      With that said both **target_usn** object and any object from **related_usns**
      follow this structure:

      * **title**: The title of the USN.
      * **description**: The USN description.
      * **error**: Any error captured when fixing the USN will appear here. The error object
                  will be detailed in a following section.
      * **status**: The expected status of the USN after the fix operation. There are
        three possible scenarios: **fixed**, **still-affected** and **not-affected**.
        The system is considered **still-affected** if there is something that
        prevents any required packages from being upgraded. The system
        is considered **not-affected** if the USN doesn't affect the system at all.
      * **upgraded_packages**: A list of UpgradedPackage objects referencing each package
        that was upgraded during the fix operation. The UpgradedPackage object always contain
        the **name** of the package, the **version** it was upgraded to and the **pocket** where
        the package upgrade came from.

      **What errors can be generated?**

      There some errors that can happen when executing this endpoint. For example, the system
      might require the user to attach to a Pro subscription to install the upgrades,
      or the user might run the command as non-root when a package upgrade is needed.

      In those situations, the error JSON error object will follow this representation:

      .. code-block:: json

         {
           "error_type": "error-type",
           "reason": "reason",
           "failed_upgrades": [
             {
               "name": "pkg1",
               "pocket": "esm-infra"
             }
           ]
         }

      We can see that the representation has the following fields:

      * **error_type**: The error type
      * **reason**: The explanation of why the error happened
      * **failed_upgrade**: A list of objects that always contain the name of the package
        that was not upgraded and the pocket where the upgrade would have come from.

u.pro.security.fix.usn.plan.v1
===============================

This endpoint shows the necessary steps required to fix USNs in the system without
executing any of those steps.

- Introduced in Ubuntu Pro Client Version: ``29~``
- Args:

  - ``usns``: A list of USNs (i.e. USN-6119-1) titles

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.pro.security.fix.usn.plan.v1 import plan, USNFixPlanOptions

           options = USNFixPlanOptions(cves=["USN-1234-1", "USN-1235-1"])
           result = plan(options)

      - Expected return object:

        - ``uaclient.api.u.pro.security.fix.cve.plan.v1.USNSFixPlanResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``usns_data``
               - ``List[USNFixPlanResult]``
               - A list of ``USNFixPlanResult`` objects

        - ``uaclient.api.u.pro.security.fix.cve.plan.v1.USNFixPlanResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``expected_status``
               - ``str``
               - The expected status of fixing the USNs
             * - ``cves``
               - ``List[FixPlanUSNResult]``
               - A list of FixPlanUSNResult objects

        - ``uaclient.api.u.pro.security.fix.FixPlanUSNResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``target_usn_plan``
               - ``FixPlanResult``
               - A ``FixPlanResult`` object for the target USN
             * - ``related_usns_plan``
               - ``List[FixPlanResult]``
               - A list of ``FixPlanResult`` objects for the related USNs

        - ``uaclient.api.u.pro.security.fix.FixPlanResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``title``
               - ``str``
               - The title of the USN
             * - ``expected_status``
               - ``str``
               - The expected status of fixing the USN
             * - ``plan``
               - ``List[FixPlanStep]``
               - A list of FixPlanStep objects
             * - ``warnings``
               - ``List[FixPlanWarning]``
               - A list of FixPlanWarning objects
             * - ``error``
               - ``Optional[FixPlanError]``
               - A list of FixPlanError objects
             * - ``additional_data``
               - ``AdditionalData``
               - Additional data for the USN

        - ``uaclient.api.u.pro.security.fix import FixPlanStep``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``operation``
               - ``str``
               - The operation that would be performed to fix the USN
             * - ``order``
               - ``int``
               - The execution order of the operation
             * - ``data``
               - ``object``
               - A data object that can be either an ``AptUpgradeData``, ``AttachData``, ``EnableData``, ``NoOpData``

        - ``uaclient.api.u.pro.security.fix import FixPlanWarning``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``warning_type``
               - ``str``
               - The type of warning
             * - ``order``
               - ``int``
               - The execution order of the operation
             * - ``data``
               - ``object``
               - A data object that represents either an PackageCannotBeInstalledData or a SecurityIssueNotFixedData

        - ``uaclient.api.u.pro.security.fix import FixPlanError``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``msg``
               - ``str``
               - The error message
             * - ``code``
               - ``str``
               - The message code

        - ``uaclient.api.u.pro.security.fix.AdditionalData``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``associated_cves``
               - ``List[str]``
               - The associated CVEs for the USN
             * - ``associated_launchpad_bugs``
               - ``List[str]``
               - The associated Launchpad bugs for the USN


        - ``uaclient.api.u.pro.security.fix import AptUpgradeData``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``binary_packages``
               - ``List[str]``
               - A list of binary packages that need to be upgraded
             * - ``source_packages``
               - ``List[str]``
               - A list of source packages that need to be upgraded
             * - ``pocket``
               - ``str``
               - The pocket where the packages will be installed from

        - ``uaclient.api.u.pro.security.fix import AttachData``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``reason``
               - ``str``
               - The reason why an attach operation is needed
             * - ``source_packages``
               - ``List[str]``
               - The source packages that require the attach operation
             * - ``required_service``
               - ``str``
               - The required service that requires the attach operation

        - ``uaclient.api.u.pro.security.fix import EnableData``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``service``
               - ``str``
               - The Pro client service that needs to be enabled
             * - ``source_packages``
               - ``str``
               - The source packages that require the service to be enabled

        - ``uaclient.api.u.pro.security.fix import NoOpData``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``status``
               - ``str``
               - The status of the USN when no operation can be performed

        - ``uaclient.api.u.pro.security.fix.NoOpAlreadyFixedData``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``status``
               - ``str``
               - The status of the CVE when no operation can be performed
             * - ``source_packages``
               - ``str``
               - The source packages that are already fixed
             * - ``pocket``
               - ``str``
               - The pocket where the packages would have been installed from

        - ``uaclient.api.u.pro.security.fix import PackageCannotBeInstalledData``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``binary_package``
               - ``str``
               - The binary package that cannot be installed
             * - ``binary_package_version``
               - ``str``
               - The version of the binary package that cannot be installed
             * - ``source_package``
               - ``str``
               - The source package associated with the binary package
             * - ``related_source_packages``
               - ``List[str]``
               - A list of source packages that comes from the same pocket as the affected package
             * - ``pocket``
               - ``str``
               - The pocket where the affected package should be installed from

        - ``uaclient.api.u.pro.security.fix import SecurityIssueNotFixedData``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``source_packages``
               - ``List[str]``
               - A list of source packages that cannot be fixed at the moment
             * - ``status``
               - ``str``
               - The status of the USN regarding those packages

      - Raised exceptions:

        - No exceptions raised by this endpoint.   

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.pro.security.fix.usn.plan.v1 --data '{"usns": ["USN-1234-1", "USN-1235-1"]}'

      - Expected attributes in JSON structure:

        .. code-block:: json

           {
              "usns_data": {
                  "expected_status": "fixed",
                  "usns": [
                    {
                        "related_usns_plan": [],
                        "target_usn_plan": {
                            "title": "USN-1234-5",
                            "expected_status": "fixed",
                            "plan": [
                                {
                                    "operation": "apt-upgrade",
                                    "order": 1,
                                    "data": {
                                        "binary_packages": ["pkg1"],
                                        "source_packages": ["pkg1"],
                                        "pocket": "standard-updates"
                                    }
                                }
                            ],
                            "warnings": [],
                            "error": null,
                            "additional_data": {
                                "associated_cves": [
                                    "CVE-1234-56789"
                                ],
                                "associated_launchpad_bus": [
                                    "https://launchpad.net/bugs/BUG_ID"
                                ]
                            }
                        },
                    }
                  ]
              }
           }

u.pro.security.status.livepatch_cves.v1
=======================================

This endpoint lists Livepatch patches for the currently-running kernel.

- Introduced in Ubuntu Pro Client Version: ``27.12~``
- Args:

  - This endpoint takes no arguments.

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.pro.security.status.livepatch_cves.v1 import livepatch_cves

           result = livepatch_cves()

      - Expected return object:

        - ``uaclient.api.u.pro.security.status.livepatch_cves.v1.LivepatchCVEsResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``fixed_cves``
               - ``list(LivepatchCVEObject)``
               - List of Livepatch patches for the given system

        - ``uaclient.api.u.pro.security.status.livepatch_cves.v1.LivepatchCVEObject``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``name``
               - ``str``
               - Name (ID) of the CVE
             * - ``patched``
               - ``bool``
               - Livepatch has patched the CVE

      - Raised exceptions:

        - No exceptions raised by this endpoint.

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.pro.security.status.livepatch_cves.v1

      - Expected attributes in JSON structure:

      .. code-block:: json

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

u.pro.security.status.reboot_required.v1
========================================

This endpoint informs if the system should be rebooted or not. Possible outputs
are:

#. ``yes``: The system should be rebooted.
#. ``no``: There is no known need to reboot the system.
#. ``yes-kernel-livepatches-applied``: There are Livepatch patches applied to 
   the current kernel, but a reboot is required for an update to take place.
   This reboot can wait until the next maintenance window.

- Introduced in Ubuntu Pro Client Version: ``27.12~``
- Args:

  - This endpoint takes no arguments.

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.pro.security.status.reboot_required.v1 import reboot_required

           result = reboot_required()

      - Expected return object:

        - ``uaclient.api.u.pro.security.status.reboot_required.v1.RebootRequiredResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``reboot_required``
               - ``str``
               - One of the descriptive strings indicating if the system should
                 be rebooted

      - Raised exceptions:

        - No exceptions raised by this endpoint.

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.pro.security.status.reboot_required.v1

      - Expected attributes in JSON structure:

        .. code-block:: json

           {
               "reboot_required": "yes|no|yes-kernel-livepatches-applied"
           }

u.pro.services.dependencies.v1
========================================

This endpoint will return a full list of all service dependencies,
regardless of the current system state. That means it will always return
the same thing until new services are added, or until we add/remove
dependencies between services.

- Introduced in Ubuntu Pro Client Version: ``32~``
- Args:

  - This endpoint takes no arguments.

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.pro.services.dependencies.v1 import dependencies
           result = dependencies()

      - Expected return object:

        - ``uaclient.api.u.pro.services.dependencies.v1.DependenciesResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``services``
               - ``List[ServiceWithDependencies]``
               - Each Pro service gets an item in this list

        - ``uaclient.api.u.pro.services.dependencies.v1.ServiceWithDependencies``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``name``
               - ``str``
               - Name of the Pro service this item corresponds to
             * - ``incompatible_with``
               - ``List[ServiceWithReason]``
               - List of Pro services this service is incompatible with. That means they cannot be enabled at the same time.
             * - ``depends_on``
               - ``List[ServiceWithReason]``
               - List of Pro services this service depends on. The services in this list must be enabled for this service to be enabled.

        - ``uaclient.api.u.pro.services.dependencies.v1.ServiceWithReason``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``name``
               - ``str``
               - Name of the Pro service this item corresponds to
             * - ``reason``
               - ``Reason``
               - Reason that this service is in the list it is in.

        - ``uaclient.api.u.pro.services.dependencies.v1.Reason``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``code``
               - ``str``
               - Short string that represents the reason.
             * - ``title``
               - ``str``
               - Longer string describing the reason - possibly translated.

      - Raised exceptions:

        - No exceptions raised by this endpoint.

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.pro.services.dependencies.v1

      - Expected attributes in JSON structure:

        .. code-block:: js

            {
              "services": [
                {
                  "name": "one",
                  "depends_on": [
                    {
                      "name": "zero",
                      "reason": {
                        "code": "one-and-zero",
                        "title": "Service One requires service Zero."
                      }
                    },
                    ...
                  ],
                  "incompatible_with": [
                    {
                      "name": "two",
                      "reason": {
                        "code": "one-and-two",
                        "title": "Services One and Two are not compatible."
                      }
                    },
                    ...
                  ]
                },
                ...
              ]
            }

u.pro.services.disable.v1
=========================

Disable a Pro service. This will automatically disable any services that
depend on the target service.

- Introduced in Ubuntu Pro Client Version: ``32~``
- Args:

  .. list-table::
    :header-rows: 1

    * - Field Name
      - Type
      - Description
    * - ``service``
      - ``str``
      - Pro service to disable
    * - ``purge``
      - ``Optional[bool]``
      - Also remove all packages that were installed from this service. Only supported by some services. (default: false)

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

            from uaclient.api.u.pro.services.disable.v1 import disable, DisableOptions
            result = disable(DisableOptions(service="usg"))

      - Expected return object:

        - ``uaclient.api.u.pro.services.disable.v1.DisableResult``

          .. list-table::
            :header-rows: 1

            * - Field Name
              - Type
              - Description
            * - ``disabled``
              - ``List[str]``
              - List of services disabled

      - Raised exceptions:

        - ``NonRootUserError``: When called as non-root user
        - ``UnattachedError``: When called on a machine that is not attached to a Pro subscription
        - ``EntitlementNotFoundError``: When the service argument is not a valid Pro service name
        - ``LockHeldError``: When another Ubuntu Pro related operation is in progress
        - ``EntitlementNotDisabledError``: When the service fails to disable

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.pro.services.disable.v1 --args service=usg

      - Expected attributes in JSON structure:

        .. code-block:: js

            {
                "disabled": [
                    "usg"
                ]
            }

u.pro.services.enable.v1
========================

Enable a Pro service. This will automatically disable incompatible services
and enable required services that that target service depends on.

- Introduced in Ubuntu Pro Client Version: ``32~``
- Args:

  .. list-table::
    :header-rows: 1

    * - Field Name
      - Type
      - Description
    * - ``service``
      - ``str``
      - Pro service to be enabled
    * - ``variant``
      - ``Optional[str]``
      - Optional variant of the Pro service to be enabled.
    * - ``access_only``
      - ``Optional[bool]``
      - If true and the target service supports it, only enable access to the service (default: false)

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

            from uaclient.api.u.pro.services.enable.v1 import enable, EnableOptions
            result = enable(EnableOptions(service="usg"))

      - Expected return object:

        - ``uaclient.api.u.pro.services.enable.v1.EnableResult``

          .. list-table::
            :header-rows: 1

            * - Field Name
              - Type
              - Description
            * - ``enabled``
              - ``List[str]``
              - List of services that were enabled.
            * - ``disabled``
              - ``List[str]``
              - List of services that were disabled.
            * - ``reboot_required``
              - ``bool``
              - True if one of the services that was enabled requires a reboot.
            * - ``messages``
              - ``List[str]``
              - List of information message strings about the service that was just enabled. Possibly translated.

      - Raised exceptions:

        - ``NonRootUserError``: When called as non-root user
        - ``UnattachedError``: When called on a machine that is not attached to a Pro subscription
        - ``NotSupported``: When called for a service that doesn't support being enabled via API (currently only Landscape)
        - ``EntitlementNotFoundError``: When the service argument is not a valid Pro service name or if the variant is not a valid variant of the target service
        - ``LockHeldError``: When another Ubuntu Pro related operation is in progress
        - ``EntitlementNotEnabledError``: When the service fails to enable

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.pro.services.enable.v1 --args service=usg

      - Expected attributes in JSON structure:

        .. code-block:: js

            {
                "disabled": [],
                "enabled": [
                    "usg"
                ],
                "messages": [],
                "reboot_required": false
            }

u.pro.status.enabled_services.v1
================================

This endpoint shows the Pro services that are enabled on the machine.

- Introduced in Ubuntu Pro Client Version: ``28~``
- Args:

  - This endpoint takes no arguments.

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.pro.status.enabled_services.v1 import enabled_services

           result = enabled_services()

      - Expected return object:

        - ``uaclient.api.u.pro.status.enabled_services.v1.EnabledServicesResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``enabled_services``
               - ``List[EnabledService]``
               - A list of ``EnabledService`` objects

        - ``uaclient.api.u.pro.status.enabled_services.v1.EnabledService``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``name``
               - ``str``
               - | Name of the service.
                 | Possible values are: ``cc-eal``, ``cis``, ``esm-apps``, ``esm-infra``, ``fips``, ``fips-updates``, ``livepatch``, ``realtime-kernel``, ``ros``, ``ros-updates``.
                 | When ``usg`` is enabled, this value will be ``cis``.
             * - ``variant_enabled``
               - ``bool``
               - If a variant of the service is enabled
             * - ``variant_name``
               - ``Optional[str]``
               - Name of the variant, if a variant is enabled

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.pro.status.enabled_services.v1

u.pro.status.is_attached.v1
===========================

This endpoint shows if the machine is attached to a Pro subscription.

- Introduced in Ubuntu Pro Client Version: ``28~``
- Args:

  - This endpoint takes no arguments.

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.pro.status.is_attached.v1 import is_attached

           result = is_attached()

      - Expected return object:

        - ``uaclient.api.u.pro.status.is_attached.v1.IsAttachedResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``is_attached``
               - ``bool``
               - If the machine is attached to a Pro subscription
             * - ``contract_status``
               - ``str``
               - The current contract status (active, grace-period, active-soon-to-expire, expired).
                 Please refer to the explanation tab for a description of each state.
             * - ``contract_remaining_days``
               - ``int``
               - The number of days remaining for the contract to be valid
             * - ``is_attached_and_contract_valid``
               - ``bool``
               - If the machine is attached and the contract is still valid

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.pro.status.is_attached.v1
           
   .. tab-item:: Explanation
      :sync: explanation

      The ``contract_status`` field can return 4 different states, they are:

      * **active**: The contract is currently valid.
      * **grace-period**: The contract is in the grace period. This means that it is expired,
        but there are still some days where the contract will be valid.
      * **active-soon-to-expire**: The contract is almost expired, but still valid.
      * **expired**: The contract is expired and no longer valid.

u.apt_news.current_news.v1
==============================

This endpoint returns the current APT News that gets displayed in `apt upgrade`.

- Introduced in Ubuntu Pro Client Version: ``29~``
- Args:

  - This endpoint takes no arguments.

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.apt_news.current_news.v1 import current_news

           result = current_news().current_news

      - Expected return object:

        - ``uaclient.api.u.apt_news.current_news.v1.CurrentNewsResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``current_news``
               - ``Optional[str]``
               - | The current APT News to be displayed for the system. This could be a str with up to three lines (i.e. up to two ``\n`` characters).
                 | If there is no APT News to be displayed, this will be ``None``.
      - Raised exceptions:

        - No exceptions raised by this endpoint.

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.apt_news.current_news.v1

      - Expected attributes in JSON structure:

        .. code-block:: json

           {
               "current_news":"This is a news message.\nThis is the second line of the message.\nAnd this is the third line."
           }

u.security.package_manifest.v1
==============================

This endpoint returns the status of installed packages (``apt`` and ``snap``),
formatted as a manifest file (i.e., ``package_name\tversion``).

- Introduced in Ubuntu Pro Client Version: ``27.12~``
- Args:

  - This endpoint takes no arguments.

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.security.package_manifest.v1 import package_manifest

           result = package_manifest()

      - Expected return object:

        - ``uaclient.api.u.security.package_manifest.v1.PackageManifestResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``manifest_data``
               - ``str``
               - Manifest of ``apt`` and ``snap`` packages installed on the system

      - Raised exceptions:

        - No exceptions raised by this endpoint.   

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.security.package_manifest.v1

      - Expected attributes in JSON structure:

        .. code-block:: json

           {
               "package_manifest":"package1\t1.0\npackage2\t2.3\n"
           }

u.unattended_upgrades.status.v1
===============================

This endpoint returns the status around ``unattended-upgrades``. The focus of
the endpoint is to verify if the application is running and how it is
configured on the machine.

.. important::

   For this endpoint, we deliver a unique key under ``meta`` called
   ``raw_config``. This field contains all related ``unattended-upgrades``
   configurations, unparsed. This means that this field will maintain both
   original name and values for those configurations.

- Introduced in Ubuntu Pro Client Version: ``27.14~``
- Args:

  - This endpoint takes no arguments.

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

           from uaclient.api.u.unattended_upgrades.status.v1 import status

           result = status()

      - Expected return object:

        - ``uaclient.api.u.unattended_upgrades.status.v1.UnattendedUpgradesStatusResult``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``systemd_apt_timer_enabled``
               - ``bool``
               - Indicate if the ``apt-daily.timer`` jobs are enabled
             * - ``apt_periodic_job_enabled``
               - ``bool``
               - Indicate if the ``APT::Periodic::Enabled`` configuration is turned off
             * - ``package_lists_refresh_frequency_days``
               - ``int``
               - The value of the ``APT::Periodic::Update-Package-Lists`` configuration
             * - ``unattended_upgrades_frequency_days``
               - ``int``
               - The value of the ``APT::Periodic::Unattended-Upgrade`` configuration
             * - ``unattended_upgrades_allowed_origins``
               - ``List[str]``
               - The value of the ``Unattended-Upgrade::Allowed-Origins`` configuration
             * - ``unattended_upgrades_running``
               - ``bool``
               - Indicate if the ``unattended-upgrade`` service is correctly configured and running
             * - ``unattended_upgrades_disabled_reason``
               - ``object``
               - Object that explains why ``unattended-upgrades`` is not running -- if the application is running, the object will be null
             * - ``unattended_upgrades_last_run``
               - ``datetime.datetime``
               - The last time ``unattended-upgrades`` ran

        - ``uaclient.api.u.unattended_upgrades.status.v1.UnattendedUpgradesStatusDisabledReason``

          .. list-table::
             :header-rows: 1

             * - Field Name
               - Type
               - Description
             * - ``msg``
               - ``str``
               - The reason why ``unattended-upgrades`` is not running on the system
             * - ``code``
               - ``str``
               - The message code associated with the message

      - Raised exceptions:

        - ``UnattendedUpgradesError``: Raised if we cannot run a necessary command to show the status of ``unattended-upgrades``.

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           pro api u.unattended_upgrades.status.v1

      - Expected attributes in JSON structure:

        .. code-block:: json

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

      - Possible attributes in JSON ``meta`` field:

        .. code-block:: json

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
