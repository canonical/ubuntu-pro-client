What does ``security-status`` do?
*********************************

The ``security-status`` command provides an overview of all the packages
installed on your machine, and the security coverage that applies to those
packages.

The output of the ``security-status`` command varies, depending on the
configuration of the machine you run it on. In this article, we'll take a look
at the different outputs of ``security-status`` and the situations in which
you might see them.

Command output
==============

If you run the ``pro security-status`` command, the first blocks of information
you see look like:

.. code-block:: text

    2871 packages installed:
        2337 packages from Ubuntu Main/Restricted repository
        504 packages from Ubuntu Universe/Multiverse repository
        8 packages from third parties
        22 packages no longer available for download

    To get more information about the packages, run
        pro security-status --help
    for a list of available options.

Those are counts for the ``apt`` packages installed in the system, sorted
between the packages in main, universe, third party packages, and packages
that are no longer available. You will also see a hint to run
``pro security-status --help`` to get more information.

``apt update`` reminder
-----------------------

To get accurate package information, the ``apt`` caches must be up to date. If
your cache was not updated recently, you may see a message in the output with
a reminder to update.

.. code-block:: text

    The system apt cache may be outdated. Make sure to run
        sudo apt-get update
    to get the latest package information from apt.

LTS coverage
------------

If ``esm-infra`` is disabled in your system, main/restricted packages will be
covered during the LTS period - this information is presented right after the
hints. A covered system will present this message:

.. code-block:: text

    This machine is receiving security patching for Ubuntu Main/Restricted
    repository until <year>.

On a system where the LTS period ended, you'll see:

.. code-block:: text

    This machine is NOT receiving security patches because the LTS period has ended
    and esm-infra is not enabled.

Ubuntu Pro coverage
-------------------

An Ubuntu Pro subscription provides more security coverage than a standard LTS.
The next blocks of information are related to Ubuntu Pro itself:

.. code-block:: text

    This machine is attached to an Ubuntu Pro subscription.

    Main/Restricted packages are receiving security updates from
    Ubuntu Pro with 'esm-infra' enabled until 2032.

    Universe/Multiverse packages are receiving security updates from
    Ubuntu Pro with 'esm-apps' enabled until 2032. You have received 21 security
    updates.

This system is already attached to Pro! It is a Jammy machine, which has
installed some updates from ``esm-apps``. Running the same command on a Xenial
system without Pro enabled, the output looks like:

.. code-block:: text

    This machine is NOT attached to an Ubuntu Pro subscription.

    Ubuntu Pro with 'esm-infra' enabled provides security updates for
    Main/Restricted packages until 2026. There are 170 pending security updates.

    Ubuntu Pro with 'esm-apps' enabled provides security updates for
    Universe/Multiverse packages until 2026. There is 1 pending security update.

    Try Ubuntu Pro with a free personal subscription on up to 5 machines.
    Learn more at https://ubuntu.com/pro

There are lots of ``esm-infra`` updates for this machine, and even an
``esm-apps`` update. The hint in the end of the output has a link to the main
Pro website, so the user can learn more about Pro and get their subscription.

Interim releases
----------------

If you are running an interim release, the output is slightly different because
there are no Ubuntu Pro services available. You will still see the package
counts and support period though - your main/restricted packages are supported
for 9 months from the release date.

.. code-block:: text

    613 packages installed:
        601 packages from Ubuntu Main/Restricted repository
        12 packages from Ubuntu Universe/Multiverse repository

    To get more information about the packages, run
        pro security-status --help
    for a list of available options.

    Main/Restricted packages receive updates until 1/2024.

    Ubuntu Pro is not available for non-LTS releases.

Optional flags for specific package sets
----------------------------------------

Some flags can be passed to ``security-status`` to get information about
coverage of specific package sets. As an example, let's look at the output of
``pro security-status --esm-infra``:

.. code-block:: text

    442 packages installed:
        441 packages from Ubuntu Main/Restricted repository

    Main/Restricted packages are receiving security updates from
    Ubuntu Pro with 'esm-infra' enabled until 2026. You have received 3 security
    updates. There are 160 pending security updates.

    Run 'pro help esm-infra' to learn more

    Installed packages with an available esm-infra update:
    ( ... list of packages ... )

    Installed packages with an esm-infra update applied:
    ( ... list of packages ... )

    Further installed packages covered by esm-infra:
    ( ... list of packages ... )

    For example, run:
        apt-cache show tcpdump
    to learn more about that package.

Besides the support information of main/restricted (which Ubuntu Pro with
``esm-infra`` extends) there are lists of:

- Packages with an updated version available in ESM-infra repositories
- Packages with a version installed from the ESM-infra repositories
- Packages which are covered by ESM-infra

You will see a similar output when running ``pro security-status --esm-apps``,
but with information regarding universe/multiverse packages.

You can also get a list of the third-party packages installed in the system:

.. code-block:: text

    $ pro security-status --thirdparty
    2871 packages installed:
        8 packages from third parties

    Packages from third parties are not provided by the official Ubuntu
    archive, for example packages from Personal Package Archives in Launchpad.

    Packages:
    ( ... list of packages ... )

    For example, run:
        apt-cache show <package_name>
    to learn more about that package.

And also a list of unavailable packages (which no longer have any installation
source):

.. code-block:: text

    $ pro security-status --unavailable
    2871 packages installed:
        22 packages no longer available for download

    Packages that are not available for download may be left over from a
    previous release of Ubuntu, may have been installed directly from a
    .deb file, or are from a source which has been disabled.

    Packages:
    ( ... list of packages ... )


    For example, run:
        apt-cache show <package_name>
    to learn more about that package.

Machine-readable output
=======================

If you need a machine readable version of ``pro security-status``, you can use
these API endpoint to achieve that:

* :ref:`u.pro.packages.summary.v1 <references/api:u.pro.packages.summary.v1>`
* :ref:`u.pro.packages.updates.v1 <references/api:u.pro.packages.updates.v1>`
* :ref:`u.pro.status.is_attached.v1 <references/api:u.pro.status.is_attached.v1>`
* :ref:`u.pro.status.enabled_services.v1 <references/api:u.pro.status.enabled_services.v1>`
* :ref:`u.pro.security.status.livepatch_cves.v1 <references/api:u.pro.security.status.livepatch_cves.v1>`

``u.pro.packages.summary.v1``
------------------------------

This API is responsible for providing a summary of where all the installed packages
in the machine comes from.

When called through ``pro api u.pro.packages.summary.v1``, it will produce a data output
with the following structure:

.. code-block:: js

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

The summary object contains the following fields:

* **num_installed_packages**: The total number of installed packages on the
  system.
* **num_esm_apps_packages**: The number of packages installed from
  ``esm-apps``.
* **num_esm_infra_packages**: The number of packages installed from
  ``esm-infra``.
* **num_main_packages**: The number of packages installed from the ``main``
  archive component.
* **num_multiverse_packages**: The number of packages installed from the
  ``multiverse`` archive component.
* **num_restricted_packages**: The number of packages installed from the
  ``restricted`` archive component.
* **num_third_party_packages** : The number of packages installed from
  ``third party`` sources.
* **num_universe_packages**: The number of packages installed from the
  ``universe`` archive component.
* **num_unknown_packages**: The number of packages installed from sources not
  known to ``apt`` (e.g., those installed locally through ``dpkg`` or packages
  without a remote reference).


``u.pro.packages.updates.v1``
------------------------------

This API is responsible for listing the available package updates in the system.

When called through ``pro api u.pro.packages.updates.v1``, it will produce a data output
with the following structure:

.. code-block:: js

    {
        "summary": {
            "num_updates": 15,
            "num_esm_apps_updates": 2,
            "num_esm_infra_updates": 3,
            "num_standard_security_updates": 5,
            "num_standard_updates": 5,
        },
        "updates": [
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


Note that there are two distinct object in the JSON response, **summary** and **updates**.
The summary object will contain the following attributes:

* **num_updates**: The total number of available updates to the system.
* **num_esm_apps_updates**: The number of ``esm-apps`` package updates
  available to the system.
* **num_esm_infra_updates**: The number of ``esm-infra`` package updates
  available to the system.
* **num_standard_security_updates**: The number of standard security updates
  available to the system.
* **num_standard_updates**: The number of standard updates available to the system.

While the updates object will be a list of package updates, where each update object
will contain the following attributes:

* **download_size**: The number of bytes that would be downloaded in order to
  install the update.
* **origin**: The host where the update comes from.
* **package**: The name of the package.
* **provided_by**: The service that provides the package update. It can be
  one of: ``esm-infra``, ``esm-apps`` or ``standard-security``.
* **status**: The status for this update. It will be one of:

  * **"upgrade_available"**: The package can be upgraded right now.
  * **"upgrade_available_not_preferred"**: The package can be upgraded but the
    upgrade will not automatically selected by APT or other tools due to
    lower pinning or the existence of a higher-priority candidate.
  * **"pending_attach"**: The package needs an Ubuntu Pro subscription attached
    to be upgraded.
  * **"pending_enable"**: The machine is attached to an Ubuntu Pro subscription,
    but the service required to provide the upgrade is not enabled.
  * **"upgrade_unavailable"**: The machine is attached, but the contract is not
    entitled to the service which provides the upgrade.
* **version**: The update version.

``u.pro.status.is_attached.v1``
--------------------------------

This API is responsible for telling if the system is attached to a Pro subscription

When called through ``pro api u.pro.status.is_attached.v1``, it will produce a data output
with the following structure:

.. code-block:: js

    {
        "contract_remaining_days": 360,
        "contract_status": "active",
        "is_attached": true,
        "is_attached_and_contract_valid": true
    }

The JSON response object will contain the following fields:

* **contract_remaining_days**: The number of days left in the Ubuntu Pro subscription
* **contract_status**: The status of the Ubuntu Pro subscription:

  * **active**: The contract is currently valid.
  * **grace-period**: The contract is in the grace period. This means that
    it is expired, but there are still some days where the contract will be
    valid.
  * **active-soon-to-expire**: The contract is almost expired, but still
    valid.
  * **expired**: The contract is expired and no longer valid.

* **is_attached**:  true if the machine is attached to an Ubuntu Pro subscription
* **is_attached_and_contract_valid**: true if the machine is attached to an Ubuntu
  Pro subscription and that subscription is not expired

``u.pro.status.enabled_services.v1``
-------------------------------------

This API is responsible for telling which services are enabled in the machine.

When called through ``pro api u.pro.status.enabled_services.v1``, it will produce a data output
with the following structure:

.. code-block:: js

    {
        "enabled_services": [
            {
                "name": "esm-apps",
                "variant_enabled": false,
                "variant_name": null
            },
            {
                "name": "esm-infra",
                "variant_enabled": false,
                "variant_name": null
            },
            {
                "name": "realtime-kernel",
                "variant_enabled": true,
                "variant_name": "raspi"
            }
        ]
    }

You can see that the JSON response has an object named **enabled_services** that is a list
of services that are enabled in the machine. Each enabled service has these attributes:

* **name**: The name of the service.
* **variant_enabled**: true if a variant of the service was enable.
* **variant_name**: The variant name if **variant_enabled** is true, **null** otherwise.


``u.pro.security.status.livepatch_cves.v1``
--------------------------------------------

This endpoint lists Livepatch patches for the currently-running kernel.

When called through ``pro api u.pro.security.status.livepatch_cves.v1``, it will
produce a data output with the following structure:

.. code-block:: js

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
        ]
    }

You can see that the JSON response has an object named **fixed_cves** that is a list
of CVEs that are addressed by the current Livepatch patch. Each CVE object will have the
following attributes:

* **name**: The name of the CVE.
* **patched**: true if a CVE was patched by Livepatch patch, false otherwise.
