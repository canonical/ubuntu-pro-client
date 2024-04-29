How to enable esm-infra-legacy on Trusty
*****************************************

The ``esm-infra-legacy`` service can be enabled to grant an additional two years of 
extended security coverage. This service is only available on Trusty, since the release has reached
the end of its support period for ``esm-infra``. Check out `Canonical expands Long Term Support to 12 years
starting with Ubuntu 14.04 LTS <https://canonical.com/blog/canonical-expands-long-term-support-to-12-years-starting-with-ubuntu-14-04-lts>`_
to read on about what the service provides and for links to contact Canonical to acquire that
service.


Make sure ``ua`` is up-to-date
===============================

All Trusty systems come with ``ua`` pre-installed through the
``ubuntu-advantage-tools`` package. To make sure that you're running the latest
version of ``ua``, run the following commands:

.. code-block:: bash

    sudo apt update && sudo apt install ubuntu-advantage-tools

Note that on Trusty, Ubuntu Pro is referred to by its previous name: "Ubuntu Advantage" (or ``ua``).


Check the status of the services
================================

After you have attached to a Pro subscription and
updated the ``ubuntu-advantage-tools`` package, you can check which services
are enabled by running the following command:

.. code-block:: bash

    sudo ua status

This will show you which services are enabled or disabled on your machine,
(output truncated for brevity). With the addition of legacy support, it will
now show the esm-infra-legacy service on Trusty:

.. code-block:: text

    SERVICE          ENTITLED  STATUS    DESCRIPTION
    esm-infra        yes       enabled   Expanded Security Maintenance for Infrastructure
    esm-infra-legacy yes       disabled  Expanded Security Maintenance for Infrastructure on Legacy Instances
    livepatch        yes       enabled   Canonical Livepatch service

.. _enable_legacy:

Enabling esm-infra-legacy
==========================

If you are entitled to the esm-infra-legacy service as shown above, you can enable it by running:

.. code-block:: bash

    sudo ua enable esm-infra-legacy


What to do if esm-infra-legacy is not entitled
===============================================

If status is showing that you are not entitled to the service, you
will need to buy access to the service. You can contact sales/support for help on that regard.

Once you have bought support, you will need to run the following command
on your machine to refresh the contract definitions:

.. code-block:: bash

    sudo ua refresh


After refreshing the contract data, you can confirm that the service is now entitled by running:


.. code-block:: bash

    sudo ua status

Now that you are entitled and can go refer to this :ref:`section <enable_legacy>` to enable
the service.


Trusty caveats
===============

There are some known caveats for the Trusty version of `ubuntu-advantage-tools`:

* **Disabling esm-infra also disables esm-infra-legacy**: If you disable esm-infra that will due
  to internal dependencies also disable esm-infra-legacy. Even though further updates will only
  come in via esm-infra-legacy it is recommended to keep both enable. If desired to disable
  esm-infra-legacy, that is ok and can be done without consequences for esm-infra.
* **do-release-upgrade fails if esm-infra enabled and packages installed from it**: The
  do-release-upgrade operation will fail here, as there will be an APT dependency issue
  when performing the operation.

  You can address this issue by running do-release-upgrade with the following command:

  .. code-block:: bash

      sudo RELEASE_UPGRADER_ALLOW_THIRD_PARTY=1 do-release-upgrade
  
  However, please note you will require to re-enable the Pro services again
  once you are on Xenial, as Trusty lacks the right mechanisms to re-enable
  the Pro services automatically after do-release-upgrade.
  
It is import to say that these problems won't happen on Xenial or later.
The Ubuntu Pro Client is still fully supported on those later releases and
these issues have already been fixed for them.


Why 14.04 (Trusty) no longer receives new Ubuntu Pro Client features
---------------------------------------------------------------------

For a further reduced risk of regressions on 14.04 (Trusty) the Pro client package is almost frozen.
Hence it is not receiving regular upstream backports like newer Ubuntu LTS releases do. Beyond
version 19.7 there won't be updates except any critical CVE maintenance or features explicitly
targeted for Trusty like esm-infra-support in 2024

Version 19.7 has full-featured support of the applicable Ubuntu Pro
service offerings ``esm-infra``, ``esm-infra-legacy`` and ``livepatch``.
